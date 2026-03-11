"""Tests for pencil_mcp_tools.py — PencilMcpTools AI Agent 工具"""

import json
import pytest
from unittest.mock import patch

from airis_pdm.pencil_mcp_tools import PencilMcpTools, _ok, _err


# ── Fixtures ──

SIMPLE_PEN_DATA = {
    "type": "frame",
    "name": "TestApp",
    "width": 360,
    "height": 780,
    "fill": "#0092B8",
    "layout": "vertical",
    "gap": 16,
    "padding": {"top": 16, "left": 16, "right": 16, "bottom": 16},
    "children": [
        {
            "type": "text",
            "name": "Title",
            "content": "Hello",
            "fontSize": 18,
            "fontWeight": 600,
            "color": "#FFFFFF",
        },
    ],
}

MINIMAL_SPEC = {
    "name": "TestPage",
    "width": 360,
    "height": 780,
    "theme": {"primary": "#0092B8", "bg": "#F8FAFC"},
    "sections": [
        {"type": "header", "title": "標題", "height": 56},
    ],
}

FULL_SPEC = {
    "name": "Dashboard",
    "width": 360,
    "height": 780,
    "theme": {"primary": "#0092B8", "bg": "#F8FAFC", "textDark": "#1D293D", "textLight": "#FFFFFF"},
    "sections": [
        {"type": "header", "title": "首頁", "height": 56},
        {"type": "content"},
        {"type": "grid", "columns": 2, "items": [
            {"label": "功能A", "icon": "star"},
            {"label": "功能B", "icon": "search"},
        ]},
        {"type": "card", "title": "公告", "content": "系統維護通知"},
        {"type": "list", "title": "任務", "items": [
            {"title": "任務1", "subtitle": "未完成"},
            {"title": "任務2"},
        ]},
        {"type": "navbar", "items": [
            {"label": "首頁", "icon": "home"},
            {"label": "設定", "icon": "settings"},
        ]},
    ],
}


# ── Tests: helpers ──

class TestHelpers:
    def test_ok(self):
        result = json.loads(_ok({"key": "value"}))
        assert result["status"] == "ok"
        assert result["data"]["key"] == "value"

    def test_err(self):
        result = json.loads(_err("something failed"))
        assert result["status"] == "error"
        assert "something failed" in result["message"]


# ── Tests: get_pen_ir ──

class TestGetPenIR:
    def test_valid_input(self):
        tools = PencilMcpTools()
        result = json.loads(tools.get_pen_ir(SIMPLE_PEN_DATA))

        assert result["status"] == "ok"
        ir_doc = result["data"]
        assert ir_doc["version"] == "2.0.0"
        assert ir_doc["tree"]["figmaName"] == "TestApp"
        assert ir_doc["stats"]["nodeCount"] == 2

    def test_list_input(self):
        tools = PencilMcpTools()
        result = json.loads(tools.get_pen_ir([SIMPLE_PEN_DATA]))
        assert result["status"] == "ok"

    def test_custom_page_name(self):
        tools = PencilMcpTools(page_name="CustomPage")
        result = json.loads(tools.get_pen_ir([SIMPLE_PEN_DATA, SIMPLE_PEN_DATA]))
        ir_doc = result["data"]
        assert ir_doc["tree"]["figmaName"] == "CustomPage"


# ── Tests: generate_code ──

class TestGenerateCode:
    def test_generate_returns_result(self):
        tools = PencilMcpTools()
        with patch("airis_pdm.pencil_mcp_tools.generate_from_ir") as mock_gen:
            mock_gen.return_value = {
                "files": ["App.vue"],
                "target": "vue",
                "output_dir": "./out",
            }
            result = json.loads(tools.generate_code(SIMPLE_PEN_DATA, target="vue", output_dir="./out"))

        assert result["status"] == "ok"
        assert result["data"]["files"] == ["App.vue"]
        assert result["data"]["target"] == "vue"

    def test_generate_error_handling(self):
        tools = PencilMcpTools()
        with patch("airis_pdm.pencil_mcp_tools.generate_from_ir", side_effect=RuntimeError("fail")):
            result = json.loads(tools.generate_code(SIMPLE_PEN_DATA))

        assert result["status"] == "error"
        assert "fail" in result["message"]


# ── Tests: get_design_tokens ──

class TestGetDesignTokens:
    def test_returns_tokens(self):
        tools = PencilMcpTools()
        result = json.loads(tools.get_design_tokens(SIMPLE_PEN_DATA))

        assert result["status"] == "ok"
        tokens = result["data"]
        assert "colors" in tokens
        assert "fontSizes" in tokens
        assert "fontFamilies" in tokens


# ── Tests: get_completeness ──

class TestGetCompleteness:
    def test_simple_design(self):
        tools = PencilMcpTools()
        result = json.loads(tools.get_completeness(SIMPLE_PEN_DATA))

        assert result["status"] == "ok"
        data = result["data"]
        assert data["nodeCount"] >= 1
        assert isinstance(data["score"], int)
        assert isinstance(data["hasStyles"], bool)
        assert isinstance(data["hasText"], bool)

    def test_high_score(self):
        """有 styles、有 text、nodeCount > 5 → 高分"""
        rich_pen = {
            "type": "frame",
            "name": "Rich",
            "width": 360, "height": 780,
            "fill": "#000",
            "layout": "vertical",
            "children": [
                {"type": "text", "content": f"Item {i}", "fontSize": 14, "color": "#FFF"}
                for i in range(6)
            ],
        }
        tools = PencilMcpTools()
        result = json.loads(tools.get_completeness(rich_pen))
        # 7 nodes (>5), has styles, has text → 25+25+25+25 = 100
        assert result["data"]["score"] >= 75

    def test_empty_design(self):
        tools = PencilMcpTools()
        result = json.loads(tools.get_completeness({"type": "frame", "name": "Empty"}))
        assert result["status"] == "ok"
        assert result["data"]["score"] <= 50


# ── Tests: spec_to_design_ops ──

class TestSpecToDesignOps:
    def test_minimal_spec(self):
        tools = PencilMcpTools()
        result = json.loads(tools.spec_to_design_ops(MINIMAL_SPEC))

        assert result["status"] == "ok"
        ops = result["data"]["operations"]
        assert len(ops) >= 2  # 至少 root + header
        assert ops[0].startswith("root=I(")

    def test_empty_spec(self):
        tools = PencilMcpTools()
        result = json.loads(tools.spec_to_design_ops({"name": "Empty"}))
        assert result["status"] == "ok"
        assert len(result["data"]["operations"]) == 1  # 只有 root

    def test_full_spec_all_sections(self):
        tools = PencilMcpTools()
        result = json.loads(tools.spec_to_design_ops(FULL_SPEC))

        assert result["status"] == "ok"
        ops = result["data"]["operations"]
        ops_str = "\n".join(ops)

        # 驗證各 section type 都有產出
        assert "Header" in ops_str
        assert "Content" in ops_str
        assert "Grid" in ops_str
        assert "Card-公告" in ops_str
        assert "List" in ops_str
        assert "NavBar" in ops_str

    def test_grid_with_icons(self):
        spec = {
            "name": "GridTest",
            "sections": [
                {"type": "grid", "columns": 2, "items": [
                    {"label": "X", "icon": "star"},
                    {"label": "Y"},
                ]},
            ],
        }
        tools = PencilMcpTools()
        result = json.loads(tools.spec_to_design_ops(spec))
        ops = result["data"]["operations"]
        ops_str = "\n".join(ops)
        assert "icon_font" in ops_str
        assert "star" in ops_str

    def test_card_title_and_content(self):
        spec = {
            "name": "CardTest",
            "sections": [
                {"type": "card", "title": "T", "content": "C"},
            ],
        }
        tools = PencilMcpTools()
        result = json.loads(tools.spec_to_design_ops(spec))
        ops = result["data"]["operations"]
        # root + card frame + title text + content text = 4
        assert len(ops) == 4

    def test_navbar_items(self):
        spec = {
            "name": "NavTest",
            "sections": [
                {"type": "navbar", "items": [
                    {"label": "Home", "icon": "home"},
                    {"label": "Profile"},
                ]},
            ],
        }
        tools = PencilMcpTools()
        result = json.loads(tools.spec_to_design_ops(spec))
        ops = result["data"]["operations"]
        ops_str = "\n".join(ops)
        assert "NavBar" in ops_str
        assert "Tab-Home" in ops_str
        assert "Tab-Profile" in ops_str

    def test_description_count(self):
        tools = PencilMcpTools()
        result = json.loads(tools.spec_to_design_ops(FULL_SPEC))
        ops = result["data"]["operations"]
        desc = result["data"]["description"]
        assert str(len(ops)) in desc
