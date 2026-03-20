"""
FigmAI Chain Pipeline（純 Python）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from .chain import generate_code_artifacts
from .spec_to_design_ops import spec_to_design_ops
from .ui_ir_to_airis import airis_ir_to_ui_ir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChainStageReport:
    name: str
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


@dataclass
class ChainContext:
    spec_path: str
    output_dir: str
    target: str = "vue"
    with_utility_css: bool = False
    spec: Dict[str, Any] | None = None
    design_ops: Dict[str, Any] | None = None
    ui_ir: Dict[str, Any] | None = None
    result: Dict[str, Any] | None = None
    stages: List[ChainStageReport] = field(default_factory=list)


def _run_step(ctx: ChainContext, name: str, fn: Callable[[ChainContext], None]) -> None:
    stage = ChainStageReport(name=name, status="pending", started_at=_now_iso())
    ctx.stages.append(stage)
    try:
        fn(ctx)
        stage.status = "completed"
    except Exception as e:  # noqa: BLE001
        stage.status = "failed"
        stage.error = str(e)
        raise
    finally:
        stage.finished_at = _now_iso()


def _step_load_spec(ctx: ChainContext) -> None:
    ctx.spec = json.loads(Path(ctx.spec_path).read_text(encoding="utf-8"))


def _step_spec_to_design_ops(ctx: ChainContext) -> None:
    if not ctx.spec:
        raise ValueError("spec 尚未載入")
    ctx.design_ops = spec_to_design_ops(ctx.spec)


def _infer_figma_type(node_type: str, has_children: bool) -> str:
    t = (node_type or "").lower()
    if t in ("text", "label", "heading", "paragraph"):
        return "TEXT"
    if t in ("image", "icon", "vector", "rectangle"):
        return "RECTANGLE"
    if t in ("component", "instance"):
        return "COMPONENT"
    # button / input / link 在現有產生器用 FRAME + metadata/text 即可穩定輸出
    return "FRAME" if has_children else "FRAME"


def _style_from_props(props: Dict[str, Any]) -> Dict[str, Any]:
    styles: Dict[str, Any] = {}
    fill = props.get("fill") or props.get("backgroundColor")
    if isinstance(fill, str) and fill:
        styles["backgroundColor"] = fill
    color = props.get("color")
    if isinstance(color, str) and color:
        styles["color"] = color
    radius = props.get("cornerRadius") or props.get("borderRadius")
    if isinstance(radius, (int, float)) and radius > 0:
        styles["borderRadius"] = {
            "topLeft": radius,
            "topRight": radius,
            "bottomRight": radius,
            "bottomLeft": radius,
        }
    return styles


def _auto_layout_from_props(props: Dict[str, Any], has_children: bool) -> Dict[str, Any] | None:
    if not has_children:
        return None
    direction_raw = str(props.get("direction") or props.get("layoutMode") or props.get("layout") or "VERTICAL").upper()
    direction = "HORIZONTAL" if direction_raw in ("H", "ROW", "HORIZONTAL") else "VERTICAL"
    return {
        "direction": direction,
        "spacing": int(props.get("itemSpacing") or props.get("gap") or 8),
        "paddingTop": int(props.get("paddingTop") or props.get("padding") or 0),
        "paddingRight": int(props.get("paddingRight") or props.get("padding") or 0),
        "paddingBottom": int(props.get("paddingBottom") or props.get("padding") or 0),
        "paddingLeft": int(props.get("paddingLeft") or props.get("padding") or 0),
        "primaryAlign": "MIN",
        "counterAlign": "MIN",
        "wrap": False,
    }


def _design_ops_to_airis(node: Dict[str, Any], fallback_name: str = "Node") -> Dict[str, Any]:
    children_raw = node.get("children") or []
    name = node.get("name") or fallback_name
    node_type = str(node.get("type") or "frame")
    props = dict(node.get("props") or {})
    has_children = len(children_raw) > 0
    figma_type = _infer_figma_type(node_type, has_children)

    layout = {
        "x": float(props.get("x") or node.get("x") or 0),
        "y": float(props.get("y") or node.get("y") or 0),
        "width": float(props.get("width") or node.get("width") or 0),
        "height": float(props.get("height") or node.get("height") or 0),
    }
    out: Dict[str, Any] = {
        "figmaName": name,
        "figmaType": figma_type,
        "layout": layout,
        "children": [],
    }

    styles = _style_from_props(props)
    if styles:
        out["styles"] = styles

    al = _auto_layout_from_props(props, has_children)
    if al:
        out["autoLayout"] = al

    if figma_type == "TEXT":
        text_val = (
            props.get("text")
            or props.get("label")
            or props.get("content")
            or node.get("content")
            or name
        )
        out["text"] = {
            "characters": str(text_val),
            "fontSize": int(props.get("fontSize") or 14),
            "fontFamily": str(props.get("fontFamily") or "Inter"),
            "fontWeight": int(props.get("fontWeight") or 400),
            "lineHeight": props.get("lineHeight"),
            "letterSpacing": props.get("letterSpacing", 0),
            "textAlign": str(props.get("textAlign") or "LEFT").upper(),
            "color": str(props.get("color") or "rgb(0, 0, 0)"),
        }

    metadata: Dict[str, Any] = {}
    if node_type.lower() == "link":
        href = props.get("href") or props.get("to") or props.get("route")
        if isinstance(href, str) and href:
            metadata["href"] = href
    if metadata:
        out["metadata"] = metadata

    out["children"] = [
        _design_ops_to_airis(child, fallback_name=f"{name}-{idx+1}")
        for idx, child in enumerate(children_raw)
    ]

    # button/link/input 這類常見互動節點若無 children，補一個文字子節點以利 codegen 呈現
    if not out["children"] and node_type.lower() in ("button", "link", "input"):
        label = (
            props.get("label")
            or props.get("text")
            or props.get("placeholder")
            or name
        )
        out["children"] = [
            {
                "figmaName": f"{name}Label",
                "figmaType": "TEXT",
                "layout": {"x": 0, "y": 0, "width": 0, "height": 0},
                "text": {
                    "characters": str(label),
                    "fontSize": int(props.get("fontSize") or 14),
                    "fontFamily": str(props.get("fontFamily") or "Inter"),
                    "fontWeight": int(props.get("fontWeight") or 400),
                    "lineHeight": props.get("lineHeight"),
                    "letterSpacing": props.get("letterSpacing", 0),
                    "textAlign": str(props.get("textAlign") or "LEFT").upper(),
                    "color": str(props.get("color") or "rgb(0, 0, 0)"),
                },
                "children": [],
            }
        ]
    return out


def _step_design_ops_to_ui_ir(ctx: ChainContext) -> None:
    if not ctx.design_ops:
        raise ValueError("design ops 尚未產生")
    # 完整遞迴映射：design-ops 樹 -> airis-like -> UiIR
    airis_like = _design_ops_to_airis(ctx.design_ops, fallback_name="Component")
    ctx.ui_ir = airis_ir_to_ui_ir(airis_like)


def _step_codegen(ctx: ChainContext) -> None:
    if not ctx.ui_ir:
        raise ValueError("UiIR 尚未準備")
    ctx.result = generate_code_artifacts(
        ctx.ui_ir,
        target=ctx.target,
        output_dir=ctx.output_dir,
        page_name=ctx.spec.get("name") if ctx.spec else None,
        with_utility_css=ctx.with_utility_css,
    )


def run_chain_pipeline(
    *,
    spec_path: str,
    output_dir: str,
    target: str = "vue",
    with_utility_css: bool = False,
) -> Dict[str, Any]:
    """執行 chain-local（不透過遠端 Figma 拉取）。"""
    ctx = ChainContext(
        spec_path=spec_path,
        output_dir=output_dir,
        target=target,
        with_utility_css=with_utility_css,
    )
    _run_step(ctx, "load-spec", _step_load_spec)
    _run_step(ctx, "spec-to-design-ops", _step_spec_to_design_ops)
    _run_step(ctx, "design-ops-to-ui-ir", _step_design_ops_to_ui_ir)
    _run_step(ctx, "codegen", _step_codegen)
    return {
        "success": True,
        "stages": [s.__dict__ for s in ctx.stages],
        "result": ctx.result or {},
    }
