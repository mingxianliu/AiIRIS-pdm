"""
FigmAI flow：批次頁面輸出（語意/像素）。
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from airis_pdm.figma_console_ws import request_sync
from .from_figma import figma_node_to_ui_ir, select_figma_canvas
from .ir_contract import validate_ui_ir
from .renderers.pixel_react import render_pixel_react_component
from .renderers.pixel_vue import render_pixel_vue_sfc
from .ui_ir_to_airis import ui_ir_to_airis_ir
from airis_pdm.generator import generate_from_ir

log = logging.getLogger(__name__)


def _slug(name: str) -> str:
    s = "".join(ch.lower() if ch.isalnum() else "-" for ch in (name or "page")).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s or "page"


def _display_name_from_page(name: str, pattern: str) -> str:
    clean = (name or "").strip()
    if clean.startswith(pattern):
        clean = clean[len(pattern):].strip()
    return clean or name or "Page"


def _filter_by_keywords(nodes: List[Dict[str, Any]], include: List[str], exclude: List[str]) -> List[Dict[str, Any]]:
    include_l = [s.lower() for s in include if s]
    exclude_l = [s.lower() for s in exclude if s]
    out: List[Dict[str, Any]] = []
    for n in nodes:
        nm = str(n.get("name") or "").lower()
        if exclude_l and any(k in nm for k in exclude_l):
            continue
        if include_l and not any(k in nm for k in include_l):
            continue
        out.append(n)
    return out


def _ensure_slug_collision(nodes: List[Dict[str, Any]], pattern: str) -> List[Dict[str, Any]]:
    counter: Dict[str, int] = {}
    prepared: List[Dict[str, Any]] = []
    for n in nodes:
        display = _display_name_from_page(str(n.get("name") or "Page"), pattern)
        base = _slug(display)
        idx = counter.get(base, 0) + 1
        counter[base] = idx
        slug = base if idx == 1 else f"{base}-{idx}"
        prepared.append(
            {
                **n,
                "displayName": display,
                "slug": slug,
                "routePath": f"/{slug}",
                "collisions": idx - 1,
            }
        )
    return prepared


def _write_flow_router_files(out_root: Path, framework: str, pages: List[Dict[str, Any]]) -> None:
    """
    產出與舊 TS / Prettier 多行風格對齊的 router：
    每個陣列元素結尾加逗號、檔案結尾保留換行，利於字串級 diff。
    """
    if framework in ("vue", "both"):
        vue_root = out_root / "vue"
        route_lines = [
            f"  {{ path: '{p['routePath']}', component: () => import('./{p['slug']}/Component.vue') }},"
            for p in pages
        ]
        meta_lines = [
            f"  {{ path: '{p['routePath']}', name: {json.dumps(p['displayName'])} }},"
            for p in pages
        ]
        routes_joined = "\n".join(route_lines)
        meta_joined = "\n".join(meta_lines)
        vue_root.mkdir(parents=True, exist_ok=True)
        (vue_root / "router.ts").write_text(
            "import { type RouteRecordRaw } from 'vue-router';\n\n"
            "export const flowRoutes: RouteRecordRaw[] = [\n"
            f"{routes_joined}\n"
            "];\n\n"
            "export const flowRouteMeta: Array<{ path: string; name: string }> = [\n"
            f"{meta_joined}\n"
            "];\n",
            encoding="utf-8",
        )
    if framework in ("react", "both"):
        react_root = out_root / "react"
        route_lines = [
            f"  {{ path: '{p['routePath']}', lazy: React.lazy(() => import('./{p['slug']}/Component')) }},"
            for p in pages
        ]
        meta_lines = [
            f"  {{ path: '{p['routePath']}', name: {json.dumps(p['displayName'])} }},"
            for p in pages
        ]
        routes_joined = "\n".join(route_lines)
        meta_joined = "\n".join(meta_lines)
        react_root.mkdir(parents=True, exist_ok=True)
        (react_root / "router.tsx").write_text(
            "import React from 'react';\n\n"
            "export const flowRoutes: Array<{ path: string; lazy: React.LazyExoticComponent<React.ComponentType<any>> }> = [\n"
            f"{routes_joined}\n"
            "];\n\n"
            "export const flowRouteMeta: Array<{ path: string; name: string }> = [\n"
            f"{meta_joined}\n"
            "];\n",
            encoding="utf-8",
        )


def _canonical_flow_page_row(p: Dict[str, Any]) -> Dict[str, Any]:
    """單頁條目欄位與排序固定，與 TS 產物與 git diff 對拍一致。"""
    row = {
        "collisions": int(p.get("collisions", 0)),
        "displayName": p["displayName"],
        "nodeId": str(p["nodeId"]),
        "nodeName": p["nodeName"],
        "routePath": p["routePath"],
        "slug": p["slug"],
    }
    return dict(sorted(row.items()))


def _flow_manifest_for_disk(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    寫入 manifest.json 用的正規形：頂層鍵、counts、各 page、include/exclude 皆排序，
    避免 Python dict 插入順序或使用者輸入順序造成無雜訊 diff。
    """
    page_rows = [_canonical_flow_page_row(p) for p in manifest.get("pages", [])]
    c = manifest.get("counts") or {}
    counts = dict(
        sorted(
            {
                "collisions": int(c.get("collisions", 0)),
                "filtered": int(c.get("filtered", 0)),
                "generated": int(c.get("generated", 0)),
                "matched": int(c.get("matched", 0)),
            }.items()
        )
    )
    out: Dict[str, Any] = {
        "count": int(manifest.get("count", len(page_rows))),
        "counts": counts,
        "exclude": sorted(str(x) for x in (manifest.get("exclude") or [])),
        "fidelity": str(manifest["fidelity"]),
        "framework": str(manifest["framework"]),
        "generated": [{**row} for row in page_rows],
        "include": sorted(str(x) for x in (manifest.get("include") or [])),
        "pages": [{**row} for row in page_rows],
        "pattern": str(manifest["pattern"]),
    }
    if "host" in manifest:
        out["host"] = str(manifest["host"])
        out["port"] = int(manifest["port"])
    return dict(sorted(out.items()))


def _dump_flow_manifest_json(manifest_for_disk: Dict[str, Any]) -> str:
    """JSON 縮排與結尾換行固定。"""
    text = json.dumps(manifest_for_disk, ensure_ascii=False, indent=2)
    return text + ("\n" if not text.endswith("\n") else "")


def _build_flow_manifest(
    *,
    pattern: str,
    framework: str,
    fidelity: str,
    pages: List[Dict[str, Any]],
    host: str | None = None,
    port: int | None = None,
    include: List[str] | None = None,
    exclude: List[str] | None = None,
    matched: int | None = None,
    filtered: int | None = None,
) -> Dict[str, Any]:
    include = include or []
    exclude = exclude or []
    pages_out = list(pages)
    generated_count = len(pages_out)
    counts = {
        "matched": int(matched if matched is not None else generated_count),
        "filtered": int(filtered if filtered is not None else generated_count),
        "generated": generated_count,
        "collisions": len([p for p in pages_out if int(p.get("collisions", 0)) > 0]),
    }
    manifest: Dict[str, Any] = {
        "pattern": pattern,
        "framework": framework,
        "fidelity": fidelity,
        "include": include,
        "exclude": exclude,
        "counts": counts,
        "pages": pages_out,
        # 向後相容：保留舊欄位
        "generated": pages_out,
        "count": generated_count,
    }
    if host is not None:
        manifest["host"] = host
    if port is not None:
        manifest["port"] = port
    return manifest


def run_flow_from_file_json(
    *,
    figma_file_json_path: str,
    output_dir: str,
    pattern: str = "[Page]",
    framework: str = "both",
    fidelity: str = "semantic",
) -> Dict[str, Any]:
    """以 Figma file JSON（離線）批次輸出 flow。"""
    data = json.loads(Path(figma_file_json_path).read_text(encoding="utf-8"))
    canvas = select_figma_canvas(data, page_index=0)
    candidates = [n for n in (canvas.get("children") or []) if str(n.get("name", "")).startswith(pattern)]

    out_root = Path(output_dir) / "flow"
    generated: List[Dict[str, Any]] = []
    for node in candidates:
        name = str(node.get("name") or "Page")
        display = _display_name_from_page(name, pattern)
        slug = _slug(display)
        page_dir_vue = out_root / "vue" / slug
        page_dir_react = out_root / "react" / slug
        page_dir_vue.mkdir(parents=True, exist_ok=True)
        page_dir_react.mkdir(parents=True, exist_ok=True)

        if fidelity == "pixel":
            if framework in ("vue", "both"):
                (page_dir_vue / "Component.vue").write_text(render_pixel_vue_sfc(node), encoding="utf-8")
            if framework in ("react", "both"):
                p = render_pixel_react_component(node)
                (page_dir_react / "Component.tsx").write_text(p["tsx"], encoding="utf-8")
                (page_dir_react / "Component.css").write_text(p["css"], encoding="utf-8")
        else:
            ui = figma_node_to_ui_ir(node)
            ir = ui_ir_to_airis_ir(validate_ui_ir(ui).fixed)
            if framework in ("vue", "both"):
                generate_from_ir(ir, target="vue", output_dir=str(page_dir_vue))
            if framework in ("react", "both"):
                generate_from_ir(ir, target="react", output_dir=str(page_dir_react))

        generated.append(
            {
                "nodeId": str(node.get("id") or ""),
                "nodeName": name,
                "slug": slug,
                "routePath": f"/{slug}",
                "displayName": display,
                "collisions": 0,
            }
        )

    manifest = _build_flow_manifest(
        pattern=pattern,
        framework=framework,
        fidelity=fidelity,
        pages=generated,
    )
    on_disk = _flow_manifest_for_disk(manifest)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "manifest.json").write_text(_dump_flow_manifest_json(on_disk), encoding="utf-8")
    return on_disk


def run_flow_via_console(
    *,
    output_dir: str,
    host: str = "localhost",
    port: int = 3055,
    pattern: str = "[Page]",
    include: List[str] | None = None,
    exclude: List[str] | None = None,
    framework: str = "both",
    fidelity: str = "semantic",
    depth: int = 8,
    notify: bool = False,
    rpc_timeout: float = 120.0,
    rpc_retries: int = 0,
    rpc_retry_backoff_s: float = 0.25,
    rpc_retry_backoff_max_s: float = 2.0,
    trace_id: str | None = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """以 figma-console live RPC 批次輸出 flow（對齊舊 TS runFlow）。"""
    started = time.perf_counter()
    include = include or []
    exclude = exclude or []
    matches = request_sync(
        "searchNodes",
        {"pattern": pattern},
        host=host,
        port=port,
        timeout=rpc_timeout,
        retries=rpc_retries,
        retry_backoff_s=rpc_retry_backoff_s,
        retry_backoff_max_s=rpc_retry_backoff_max_s,
        trace_id=trace_id,
        verbose=verbose,
    ) or []
    if not isinstance(matches, list):
        raise RuntimeError("searchNodes 回傳格式不正確")
    nodes = [
        m for m in matches
        if isinstance(m, dict)
        and isinstance(m.get("id"), str)
        and isinstance(m.get("name"), str)
        and str(m.get("name")).startswith(pattern)
        and str(m.get("type")) in ("FRAME", "COMPONENT", "COMPONENT_SET")
    ]
    nodes = sorted(nodes, key=lambda x: str(x.get("name")))
    filtered = _filter_by_keywords(nodes, include, exclude)
    prepared = _ensure_slug_collision(filtered, pattern)

    out_root = Path(output_dir) / "flow"
    generated: List[Dict[str, Any]] = []
    for n in prepared:
        node_id = str(n["id"])
        node = request_sync(
            "getNode",
            {"nodeId": node_id, "depth": depth},
            host=host,
            port=port,
            timeout=rpc_timeout,
            retries=rpc_retries,
            retry_backoff_s=rpc_retry_backoff_s,
            retry_backoff_max_s=rpc_retry_backoff_max_s,
            trace_id=trace_id,
            verbose=verbose,
        )
        if not node:
            continue
        slug = str(n["slug"])
        if framework in ("vue", "both"):
            page_dir_vue = out_root / "vue" / slug
            page_dir_vue.mkdir(parents=True, exist_ok=True)
            if fidelity == "pixel":
                (page_dir_vue / "Component.vue").write_text(render_pixel_vue_sfc(node), encoding="utf-8")
            else:
                ui = figma_node_to_ui_ir(node)
                ir = ui_ir_to_airis_ir(validate_ui_ir(ui).fixed)
                generate_from_ir(ir, target="vue", output_dir=str(page_dir_vue))
        if framework in ("react", "both"):
            page_dir_react = out_root / "react" / slug
            page_dir_react.mkdir(parents=True, exist_ok=True)
            if fidelity == "pixel":
                p = render_pixel_react_component(node)
                (page_dir_react / "Component.tsx").write_text(p["tsx"], encoding="utf-8")
                (page_dir_react / "Component.css").write_text(p["css"], encoding="utf-8")
            else:
                ui = figma_node_to_ui_ir(node)
                ir = ui_ir_to_airis_ir(validate_ui_ir(ui).fixed)
                generate_from_ir(ir, target="react", output_dir=str(page_dir_react))
        generated.append(
            {
                "nodeId": node_id,
                "nodeName": n["name"],
                "slug": slug,
                "routePath": n["routePath"],
                "displayName": n["displayName"],
                "collisions": n["collisions"],
            }
        )

    _write_flow_router_files(out_root, framework, generated)
    manifest = _build_flow_manifest(
        host=host,
        port=port,
        pattern=pattern,
        framework=framework,
        fidelity=fidelity,
        include=include,
        exclude=exclude,
        pages=generated,
        matched=len(nodes),
        filtered=len(filtered),
    )
    on_disk = _flow_manifest_for_disk(manifest)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "manifest.json").write_text(_dump_flow_manifest_json(on_disk), encoding="utf-8")

    if notify:
        try:
            request_sync(
                "notify",
                {"message": f"Flow generated ({len(generated)} pages)."},
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
            pass
    if verbose:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        log.info(
            "figmai flow live completed trace_id=%s matched=%s filtered=%s generated=%s elapsed_ms=%s",
            trace_id,
            len(nodes),
            len(filtered),
            len(generated),
            elapsed_ms,
        )
    return on_disk
