"""Tests for pencil_reader.py — PencilToIR 轉換器"""

import pytest
from airis_pdm.pencil_reader import PencilToIR


# ── Fixtures ──

SIMPLE_FRAME = {
    "type": "frame",
    "id": "abc1",
    "name": "AppFrame",
    "x": 0,
    "y": 0,
    "width": 360,
    "height": 780,
    "fill": "#0092B8",
    "cornerRadius": 20,
    "clip": True,
    "layout": "vertical",
    "gap": 16,
    "padding": {"top": 16, "left": 16, "right": 16, "bottom": 16},
    "children": [
        {
            "type": "text",
            "name": "Title",
            "content": "Hello World",
            "fontSize": 18,
            "fontWeight": 600,
            "color": "#FFFFFF",
        },
        {
            "type": "icon_font",
            "icon": "search",
            "fontSize": 24,
            "color": "#FFFFFF",
            "fontFamily": "Material Icons",
        },
    ],
}

MULTI_ROOT = [
    {
        "type": "frame",
        "name": "Screen1",
        "width": 360,
        "height": 780,
        "children": [],
    },
    {
        "type": "frame",
        "name": "Screen2",
        "width": 360,
        "height": 780,
        "children": [],
    },
]

FILL_CONTAINER_NODE = {
    "type": "frame",
    "name": "FullWidth",
    "width": "fill_container",
    "height": 56,
    "layout": "horizontal",
}

RECTANGLE_NODE = {
    "type": "rectangle",
    "name": "Divider",
    "width": 360,
    "height": 1,
    "fill": "#E0E0E0",
}

REF_NODE = {
    "type": "ref",
    "name": "ButtonInstance",
    "ref": "comp_button_1",
    "width": 120,
    "height": 40,
}


# ── Tests: convert() ──

class TestPencilToIR:
    def test_convert_single_frame(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)

        assert ir_doc["version"] == "2.0.0"
        assert ir_doc["source"]["tool"] == "pencil-ai"
        assert ir_doc["tree"]["figmaName"] == "AppFrame"
        assert ir_doc["tree"]["figmaType"] == "AUTO_LAYOUT"

    def test_convert_children_count(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)
        tree = ir_doc["tree"]

        assert len(tree["children"]) == 2
        assert tree["children"][0]["figmaType"] == "TEXT"
        assert tree["children"][1]["figmaType"] == "TEXT"  # icon_font → TEXT

    def test_convert_text_props(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)
        text_node = ir_doc["tree"]["children"][0]

        assert text_node["text"]["characters"] == "Hello World"
        assert text_node["text"]["fontSize"] == 18
        assert text_node["text"]["fontWeight"] == 600

    def test_convert_icon(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)
        icon_node = ir_doc["tree"]["children"][1]

        assert icon_node["text"]["characters"] == "search"
        assert icon_node["pluginData"]["isIcon"] is True
        assert icon_node["pluginData"]["iconFont"] == "Material Icons"

    def test_convert_auto_layout(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)
        al = ir_doc["tree"]["autoLayout"]

        assert al["direction"] == "VERTICAL"
        assert al["spacing"] == 16
        assert al["paddingTop"] == 16
        assert al["paddingLeft"] == 16

    def test_convert_styles(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)
        styles = ir_doc["tree"]["styles"]

        assert len(styles["fills"]) == 1
        assert styles["fills"][0]["type"] == "SOLID"
        assert styles["borderRadius"]["topLeft"] == 20

    def test_convert_clips_content(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)
        assert ir_doc["tree"]["clipsContent"] is True

    def test_convert_multi_root(self):
        converter = PencilToIR(page_name="MultiPage")
        ir_doc = converter.convert(MULTI_ROOT)
        tree = ir_doc["tree"]

        assert tree["figmaName"] == "MultiPage"
        assert tree["figmaType"] == "FRAME"
        assert len(tree["children"]) == 2

    def test_convert_fill_container(self):
        converter = PencilToIR()
        ir_doc = converter.convert(FILL_CONTAINER_NODE)
        layout = ir_doc["tree"]["layout"]

        assert layout["width"] == "FILL"
        assert layout.get("fillWidth") is True
        assert layout["height"] == 56

    def test_convert_rectangle(self):
        converter = PencilToIR()
        ir_doc = converter.convert(RECTANGLE_NODE)
        tree = ir_doc["tree"]

        assert tree["figmaType"] == "FRAME"
        assert tree["figmaName"] == "Divider"
        assert tree["styles"]["fills"][0]["type"] == "SOLID"

    def test_convert_ref(self):
        converter = PencilToIR()
        ir_doc = converter.convert(REF_NODE)
        tree = ir_doc["tree"]

        assert tree["figmaType"] == "INSTANCE"
        assert tree["componentRef"] == "comp_button_1"

    def test_viewport_detection(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)

        assert ir_doc["viewport"]["width"] == 360
        assert ir_doc["viewport"]["height"] == 780

    def test_node_count(self):
        converter = PencilToIR()
        ir_doc = converter.convert(SIMPLE_FRAME)
        # 1 root + 2 children = 3
        assert ir_doc["stats"]["nodeCount"] == 3

    def test_convert_node_only(self):
        converter = PencilToIR()
        node = converter.convert_node_only(SIMPLE_FRAME)

        assert node["figmaName"] == "AppFrame"
        assert "version" not in node  # 不含 IR document 包裝

    def test_convert_empty_input(self):
        converter = PencilToIR()
        ir_doc = converter.convert({})
        # 空 dict 無 type，tree 為 None
        assert ir_doc["tree"] is None
        assert ir_doc["version"] == "2.0.0"

    def test_convert_nested_frame(self):
        nested = {
            "type": "frame",
            "name": "Outer",
            "width": 360,
            "height": 780,
            "children": [
                {
                    "type": "frame",
                    "name": "Inner",
                    "width": 320,
                    "height": 200,
                    "layout": "horizontal",
                    "gap": 8,
                    "children": [
                        {"type": "text", "content": "A", "fontSize": 14, "color": "#000"},
                        {"type": "text", "content": "B", "fontSize": 14, "color": "#000"},
                    ],
                },
            ],
        }
        converter = PencilToIR()
        ir_doc = converter.convert(nested)
        inner = ir_doc["tree"]["children"][0]

        assert inner["figmaType"] == "AUTO_LAYOUT"
        assert inner["autoLayout"]["direction"] == "HORIZONTAL"
        assert len(inner["children"]) == 2


class TestColorNormalization:
    def test_hex_6(self):
        converter = PencilToIR()
        assert converter._normalize_color("#FF0000") == "rgba(255,0,0,1)"

    def test_hex_3(self):
        converter = PencilToIR()
        assert converter._normalize_color("#F00") == "rgba(255,0,0,1)"

    def test_hex_8(self):
        converter = PencilToIR()
        result = converter._normalize_color("#FF000080")
        assert result.startswith("rgba(255,0,0,")

    def test_rgba_passthrough(self):
        converter = PencilToIR()
        assert converter._normalize_color("rgba(0,0,0,0.5)") == "rgba(0,0,0,0.5)"

    def test_empty_color(self):
        converter = PencilToIR()
        assert converter._normalize_color("") == "rgba(0,0,0,1)"


class TestAlignmentMapping:
    def test_start(self):
        converter = PencilToIR()
        assert converter._map_alignment("start") == "MIN"

    def test_center(self):
        converter = PencilToIR()
        assert converter._map_alignment("center") == "CENTER"

    def test_space_between(self):
        converter = PencilToIR()
        assert converter._map_alignment("space_between") == "SPACE_BETWEEN"

    def test_stretch(self):
        converter = PencilToIR()
        assert converter._map_alignment("stretch") == "STRETCH"

    def test_unknown(self):
        converter = PencilToIR()
        assert converter._map_alignment("unknown") == "MIN"
