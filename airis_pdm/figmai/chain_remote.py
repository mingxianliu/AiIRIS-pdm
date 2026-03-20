"""
FigmAI chain（遠端）：透過 figma-console 進行同步與節點拉取，再走 codegen。
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from airis_pdm.figma_console_ws import request_sync

from .from_figma import figma_node_to_ui_ir
from .ir_contract import validate_ui_ir
from .spec_to_design_ops import spec_to_design_ops
from .state_store import StateStore
from .ui_ir_to_airis import ui_ir_to_airis_ir
from airis_pdm.generator import generate_from_ir

log = logging.getLogger(__name__)


def _node_type_from_design_ops(node: Dict[str, Any]) -> str:
    """將 design-ops type 對齊到 bridge 支援的 createNode 類型。"""
    raw = str(node.get("type", "")).lower()
    if raw in ("text",):
        return "TEXT"
    if raw in ("rectangle", "image"):
        return "RECTANGLE"
    if raw in ("component",):
        return "COMPONENT"
    return "FRAME"


def _node_props(node: Dict[str, Any]) -> Dict[str, Any]:
    """抽取可安全送到 create/updateNode 的屬性。"""
    props = dict(node.get("props") or {})
    for k in ("x", "y", "width", "height", "layoutMode", "itemSpacing", "layoutAlign", "layoutGrow"):
        if k in node:
            props[k] = node[k]
    return props


def _sync_node_recursive(
    node: Dict[str, Any],
    *,
    host: str,
    port: int,
    store: StateStore,
    parent_id: Optional[str] = None,
    desired_index: Optional[int] = None,
    fallback_key: str = "root",
    seen_pencil_ids: Optional[Set[str]] = None,
    rpc_timeout: float = 120.0,
    rpc_retries: int = 0,
    rpc_retry_backoff_s: float = 0.25,
    rpc_retry_backoff_max_s: float = 2.0,
    trace_id: str | None = None,
    verbose: bool = False,
) -> str:
    """
    遞迴同步（idempotent）：
    1) 先用 mapping 對應的 figma id 做 updateNode
    2) update 失敗才 createNode
    """
    pencil_id = str(node.get("id") or fallback_key)
    if seen_pencil_ids is not None:
        seen_pencil_ids.add(pencil_id)
    mapped_id = store.get_figma_id(pencil_id)
    node_id: Optional[str] = None

    if mapped_id:
        try:
            request_sync(
                "updateNode",
                {
                    "nodeId": mapped_id,
                    "props": _node_props(node),
                },
                host=host,
                port=port,
                timeout=rpc_timeout,
                retries=rpc_retries,
                retry_backoff_s=rpc_retry_backoff_s,
                retry_backoff_max_s=rpc_retry_backoff_max_s,
                trace_id=trace_id,
                verbose=verbose,
            )
            node_id = mapped_id
        except Exception:
            node_id = None

    if not node_id:
        created = request_sync(
            "createNode",
            {
                "type": _node_type_from_design_ops(node),
                "name": node.get("name", "Node"),
                "props": _node_props(node),
                "parentId": parent_id,
            },
            host=host,
            port=port,
            timeout=rpc_timeout,
            retries=rpc_retries,
            retry_backoff_s=rpc_retry_backoff_s,
            retry_backoff_max_s=rpc_retry_backoff_max_s,
            trace_id=trace_id,
            verbose=verbose,
        )
        node_id = str((created or {}).get("id"))
        if not node_id:
            raise RuntimeError("createNode 未回傳 id")
    elif parent_id:
        # parent/index drift 修正：父層或同層順序偏移時，執行 moveNode
        try:
            current = request_sync(
                "getNode",
                {"nodeId": node_id, "depth": 0},
                host=host,
                port=port,
                timeout=rpc_timeout,
                retries=rpc_retries,
                retry_backoff_s=rpc_retry_backoff_s,
                retry_backoff_max_s=rpc_retry_backoff_max_s,
                trace_id=trace_id,
                verbose=verbose,
            ) or {}
            current_parent_id = current.get("parentId")
            need_move = False
            if current_parent_id and str(current_parent_id) != str(parent_id):
                need_move = True
            elif desired_index is not None:
                parent_snapshot = request_sync(
                    "getNode",
                    {"nodeId": parent_id, "depth": 1},
                    host=host,
                    port=port,
                    timeout=rpc_timeout,
                    retries=rpc_retries,
                    retry_backoff_s=rpc_retry_backoff_s,
                    retry_backoff_max_s=rpc_retry_backoff_max_s,
                    trace_id=trace_id,
                    verbose=verbose,
                ) or {}
                children = parent_snapshot.get("children") or []
                cur_index = next(
                    (i for i, ch in enumerate(children) if str((ch or {}).get("id")) == str(node_id)),
                    None,
                )
                if cur_index is None or int(cur_index) != int(desired_index):
                    need_move = True
            if need_move:
                payload = {"nodeId": node_id, "parentId": parent_id}
                if desired_index is not None:
                    payload["index"] = int(desired_index)
                request_sync(
                    "moveNode",
                    payload,
                    host=host,
                    port=port,
                    timeout=rpc_timeout,
                    retries=rpc_retries,
                    retry_backoff_s=rpc_retry_backoff_s,
                    retry_backoff_max_s=rpc_retry_backoff_max_s,
                    trace_id=trace_id,
                    verbose=verbose,
                )
        except Exception:
            # 若查詢 parent 失敗，不中斷整體同步
            pass

    store.set_mapping(pencil_id, node_id)
    for idx, child in enumerate(node.get("children") or []):
        child_fallback = f"{pencil_id}-{idx+1}"
        _sync_node_recursive(
            child,
            host=host,
            port=port,
            store=store,
            parent_id=node_id,
            desired_index=idx,
            fallback_key=child_fallback,
            seen_pencil_ids=seen_pencil_ids,
            rpc_timeout=rpc_timeout,
            rpc_retries=rpc_retries,
            rpc_retry_backoff_s=rpc_retry_backoff_s,
            rpc_retry_backoff_max_s=rpc_retry_backoff_max_s,
            trace_id=trace_id,
            verbose=verbose,
        )
    return node_id


def _handle_missing_nodes(
    *,
    store: StateStore,
    seen_pencil_ids: Set[str],
    strategy: str,
    host: str,
    port: int,
    rpc_timeout: float,
    rpc_retries: int,
    rpc_retry_backoff_s: float,
    rpc_retry_backoff_max_s: float,
    trace_id: str | None,
    verbose: bool,
) -> Tuple[int, int]:
    """
    對 mapping 有、但本次 spec 不存在的節點執行策略：
    - keep: 保留 mapping
    - orphan: 從 nodes 移到 orphans
    - delete: 呼叫 deleteNode 後移除 mapping（失敗則轉 orphan）
    """
    stale_ids = [pid for pid in list(store.state.nodes.keys()) if pid not in seen_pencil_ids]
    deleted = 0
    orphaned = 0

    for pencil_id in stale_ids:
        figma_id = store.state.nodes.get(pencil_id)
        if not figma_id:
            continue
        if strategy == "keep":
            continue
        if strategy == "orphan":
            store.mark_orphan(pencil_id, figma_id)
            orphaned += 1
            continue
        # strategy == delete
        try:
            ok = request_sync(
                "deleteNode",
                {"nodeId": figma_id},
                host=host,
                port=port,
                timeout=rpc_timeout,
                retries=rpc_retries,
                retry_backoff_s=rpc_retry_backoff_s,
                retry_backoff_max_s=rpc_retry_backoff_max_s,
                trace_id=trace_id,
                verbose=verbose,
            )
            if ok:
                store.remove_mapping(pencil_id)
                deleted += 1
            else:
                store.mark_orphan(pencil_id, figma_id)
                orphaned += 1
        except Exception:
            store.mark_orphan(pencil_id, figma_id)
            orphaned += 1
    return deleted, orphaned


def run_chain_remote(
    *,
    spec_path: str,
    output_dir: str,
    target: str = "vue",
    host: str = "localhost",
    port: int = 3055,
    depth: int = 8,
    sync: bool = False,
    figma_node_id: Optional[str] = None,
    with_utility_css: bool = False,
    state_dir: Optional[str] = None,
    missing_node_strategy: str = "orphan",
    rpc_timeout: float = 120.0,
    rpc_retries: int = 0,
    rpc_retry_backoff_s: float = 0.25,
    rpc_retry_backoff_max_s: float = 2.0,
    trace_id: str | None = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    完整 chain（remote）：
    spec -> design-ops -> (optional sync createNode*) -> getNode -> UiIR -> codegen
    """
    started = time.perf_counter()
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    design_ops = spec_to_design_ops(spec)
    state_base = state_dir or output_dir
    store = StateStore(state_base)
    store.load()

    target_node_id = figma_node_id or ((spec.get("meta") or {}).get("figmaNodeId"))
    synced_root_id: Optional[str] = None
    deleted_count = 0
    orphaned_count = 0
    if sync:
        seen: Set[str] = set()
        synced_root_id = _sync_node_recursive(
            design_ops,
            host=host,
            port=port,
            store=store,
            parent_id=None,
            desired_index=None,
            fallback_key=str(spec.get("name") or "root"),
            seen_pencil_ids=seen,
            rpc_timeout=rpc_timeout,
            rpc_retries=rpc_retries,
            rpc_retry_backoff_s=rpc_retry_backoff_s,
            rpc_retry_backoff_max_s=rpc_retry_backoff_max_s,
            trace_id=trace_id,
            verbose=verbose,
        )
        deleted_count, orphaned_count = _handle_missing_nodes(
            store=store,
            seen_pencil_ids=seen,
            strategy=missing_node_strategy,
            host=host,
            port=port,
            rpc_timeout=rpc_timeout,
            rpc_retries=rpc_retries,
            rpc_retry_backoff_s=rpc_retry_backoff_s,
            rpc_retry_backoff_max_s=rpc_retry_backoff_max_s,
            trace_id=trace_id,
            verbose=verbose,
        )
        target_node_id = synced_root_id
        store.save()

    if not target_node_id:
        raise ValueError("chain 需要 figma node id：請提供 --figma-node-id，或在 spec.meta.figmaNodeId 設定，或啟用 --sync")

    figma_node = request_sync(
        "getNode",
        {"nodeId": target_node_id, "depth": depth},
        host=host,
        port=port,
        timeout=rpc_timeout,
        retries=rpc_retries,
        retry_backoff_s=rpc_retry_backoff_s,
        retry_backoff_max_s=rpc_retry_backoff_max_s,
        trace_id=trace_id,
        verbose=verbose,
    )
    if not figma_node:
        raise RuntimeError(f"getNode 失敗：{target_node_id}")

    ui_ir = figma_node_to_ui_ir(figma_node)
    validation = validate_ui_ir(ui_ir)
    ir = ui_ir_to_airis_ir(validation.fixed)
    result = generate_from_ir(
        ir_data=ir,
        target=target,
        output_dir=output_dir,
        page_name=spec.get("name"),
        with_utility_css=with_utility_css,
    )
    if verbose:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        log.info(
            "figmai chain remote completed trace_id=%s sync=%s deleted=%s orphaned=%s files=%s elapsed_ms=%s",
            trace_id,
            sync,
            deleted_count,
            orphaned_count,
            len(result.get("files", [])),
            elapsed_ms,
        )
    return {
        "success": True,
        "target_node_id": target_node_id,
        "synced_root_id": synced_root_id,
        "state_file": str(store.file_path.resolve()),
        "missing_node_strategy": missing_node_strategy,
        "deleted_count": deleted_count,
        "orphaned_count": orphaned_count,
        "validation": {
            "valid": validation.valid,
            "issues": [
                {"level": "error", "code": "IR_VALIDATION_ERROR", "message": msg}
                for msg in validation.errors
            ],
        },
        "generated_files": result.get("files", []),
        "output_dir": result.get("output_dir", output_dir),
    }
