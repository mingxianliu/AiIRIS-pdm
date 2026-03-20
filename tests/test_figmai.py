"""FigmAI 對齊層：UiIR 與 FigmaToIR／codegen IR 往返。"""

from airis_pdm.figma_reader import FigmaToIR
from airis_pdm.figmai import (
    airis_ir_to_ui_ir,
    figma_api_file_to_ui_ir_document,
    figma_node_to_ui_ir,
    load_ui_ir_tree_from_file_payload,
    ui_ir_to_airis_ir,
)
from airis_pdm.figmai.style_schema import compute_inline_style_map


def _minimal_file_api_json() -> dict:
    """單頁、單畫布＋一個 FRAME 的離線測試用 Figma file 形狀。"""
    return {
        "name": "Demo",
        "document": {
            "id": "0:0",
            "name": "Document",
            "type": "DOCUMENT",
            "children": [
                {
                    "id": "0:1",
                    "name": "Page",
                    "type": "CANVAS",
                    "visible": True,
                    "children": [
                        {
                            "type": "FRAME",
                            "name": "Root",
                            "visible": True,
                            "absoluteBoundingBox": {
                                "x": 0,
                                "y": 0,
                                "width": 100,
                                "height": 50,
                            },
                            "children": [
                                {
                                    "type": "TEXT",
                                    "name": "Label",
                                    "visible": True,
                                    "characters": "Hi",
                                    "style": {
                                        "fontSize": 14,
                                        "fontFamily": "Inter",
                                        "fontWeight": 400,
                                        "textAlignHorizontal": "LEFT",
                                    },
                                    "absoluteBoundingBox": {
                                        "x": 0,
                                        "y": 0,
                                        "width": 20,
                                        "height": 20,
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    }


def test_figma_node_to_ui_ir():
    fig = _minimal_file_api_json()["document"]["children"][0]["children"][0]
    ui = figma_node_to_ui_ir(fig)
    assert ui["name"] == "Root"
    assert ui["sourceType"] == "FRAME"
    assert "style" in ui and "box-sizing" in ui["style"]
    assert len(ui["children"]) == 1
    assert ui["children"][0]["name"] == "Label"


def test_ui_ir_roundtrip_matches_figma_to_ir():
    fig = _minimal_file_api_json()["document"]["children"][0]["children"][0]
    c = FigmaToIR().convert(fig)
    ui = airis_ir_to_ui_ir(c)
    c2 = ui_ir_to_airis_ir(ui)
    assert c2["figmaName"] == c["figmaName"]
    assert c2["figmaType"] == c["figmaType"]
    assert c2["children"][0]["text"]["characters"] == "Hi"


def test_figma_api_file_to_ui_ir_document():
    doc = figma_api_file_to_ui_ir_document(_minimal_file_api_json(), page_index=0)
    assert doc["format"] == "aipdm-ui-ir"
    assert doc["version"] == 1
    tree = load_ui_ir_tree_from_file_payload(doc)
    assert tree["name"] == "Page"


def test_load_ui_ir_tree_from_raw_root():
    fig = _minimal_file_api_json()["document"]["children"][0]
    ui_root = figma_node_to_ui_ir(fig)
    loaded = load_ui_ir_tree_from_file_payload(ui_root)
    assert loaded["name"] == "Page"


def test_compute_inline_style_map():
    frag = {
        "figmaType": "TEXT",
        "layout": {"width": 10, "height": 12, "x": 0, "y": 0},
        "styles": {},
        "text": {
            "characters": "x",
            "fontSize": 12,
            "fontFamily": "Inter",
            "fontWeight": 400,
            "textAlign": "LEFT",
            "color": "rgb(0, 0, 0)",
        },
    }
    css = compute_inline_style_map(frag)
    assert "font-size" in css
