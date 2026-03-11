"""Tests for generator module — pure functions (no Figma API needed)."""

import pytest

from airis_pdm.generator import (
    StyleSheet,
    StyleBundle,
    _sanitize_name,
    _kebab,
    parse_component_variant,
    select_pages,
    _collect_components,
    _style_dict,
    _render_html,
    _render_react,
    _render_vue,
    _render_flutter,
    ComponentSpec,
)


# ─── _sanitize_name ─────────────────────────────────────────────────────────


class TestSanitizeName:
    def test_simple(self):
        assert _sanitize_name("login form") == "LoginForm"

    def test_special_chars(self):
        assert _sanitize_name("my--component_v2") == "MyComponentV2"

    def test_empty_string(self):
        assert _sanitize_name("") == "Unnamed"

    def test_only_symbols(self):
        assert _sanitize_name("---") == "Unnamed"


# ─── _kebab ──────────────────────────────────────────────────────────────────


class TestKebab:
    def test_simple(self):
        assert _kebab("MyButton") == "mybutton"

    def test_spaces_and_dashes(self):
        assert _kebab("Header Nav Bar") == "header-nav-bar"

    def test_empty(self):
        assert _kebab("") == "unnamed"

    def test_special_chars_collapse(self):
        result = _kebab("a--b  c")
        assert "--" not in result


# ─── parse_component_variant ──────────────────────────────────────────────────


class TestParseComponentVariant:
    def test_simple_variant(self):
        assert parse_component_variant("Button/Primary") == ("Button", "Primary")

    def test_no_variant(self):
        assert parse_component_variant("Header") == ("Header", "Default")

    def test_empty(self):
        assert parse_component_variant("") == ("Unnamed", "Default")

    def test_multiple_slashes(self):
        comp, var = parse_component_variant("Card/Hover/Large")
        assert comp == "Card"
        assert var == "Hover"  # second part


# ─── select_pages ──────────────────────────────────────────────────────────


class TestSelectPages:
    def setup_method(self):
        self.doc = {
            "children": [
                {"name": "Home"},
                {"name": "Login"},
                {"name": "Dashboard"},
            ]
        }

    def test_all_pages(self):
        assert len(select_pages(self.doc, None, None, all_pages=True)) == 3

    def test_by_name(self):
        result = select_pages(self.doc, "Login", None, False)
        assert len(result) == 1
        assert result[0]["name"] == "Login"

    def test_by_index(self):
        result = select_pages(self.doc, None, 2, False)
        assert result[0]["name"] == "Dashboard"

    def test_name_not_found(self):
        assert select_pages(self.doc, "NotExist", None, False) == []

    def test_index_out_of_range(self):
        assert select_pages(self.doc, None, 99, False) == []

    def test_empty_doc(self):
        assert select_pages({"children": []}, None, None, True) == []

    def test_default_first_page(self):
        result = select_pages(self.doc, None, None, False)
        assert result[0]["name"] == "Home"


# ─── StyleSheet ──────────────────────────────────────────────────────────────


class TestStyleSheet:
    def test_add_node(self):
        sheet = StyleSheet(prefix="app")
        cls = sheet.add_node({"figmaName": "Header", "layout": {"width": 100, "height": 50}})
        assert cls.startswith("app-header-")
        assert len(sheet.rules) == 1

    def test_to_css(self):
        sheet = StyleSheet(prefix="cmp")
        sheet.add_node({
            "figmaName": "Box",
            "layout": {"width": 200, "height": 100},
            "styles": {"backgroundColor": "#ff0"},
        })
        css = sheet.to_css()
        assert ".cmp-box-" in css
        assert "width: 200px" in css

    def test_empty_sheet(self):
        sheet = StyleSheet(prefix="x")
        assert sheet.to_css() == ""


# ─── StyleBundle ────────────────────────────────────────────────────────────


class TestStyleBundle:
    def test_combine(self):
        s1 = StyleSheet(prefix="a")
        s1.add_node({"figmaName": "One", "layout": {"width": 10}})
        s2 = StyleSheet(prefix="b")
        s2.add_node({"figmaName": "Two", "layout": {"width": 20}})
        bundle = StyleBundle(sheets=[])
        bundle.add(s1)
        bundle.add(s2)
        css = bundle.to_css()
        assert ".a-one-" in css
        assert ".b-two-" in css


# ─── _style_dict ────────────────────────────────────────────────────────────


class TestStyleDict:
    def test_basic_layout(self):
        node = {"layout": {"width": 100, "height": 50}, "styles": {}}
        d = _style_dict(node)
        assert d["width"] == "100px"
        assert d["height"] == "50px"
        assert d["box-sizing"] == "border-box"

    def test_background_color(self):
        node = {"layout": {}, "styles": {"backgroundColor": "#ff0"}}
        d = _style_dict(node)
        assert d["background-color"] == "#ff0"

    def test_auto_layout_flex(self):
        node = {
            "layout": {},
            "styles": {},
            "autoLayout": {
                "direction": "HORIZONTAL",
                "spacing": 8,
                "paddingTop": 4,
                "paddingRight": 4,
                "paddingBottom": 4,
                "paddingLeft": 4,
                "primaryAlign": "CENTER",
                "counterAlign": "CENTER",
            },
        }
        d = _style_dict(node)
        assert d["display"] == "flex"
        assert d["flex-direction"] == "row"
        assert d["gap"] == "8px"
        assert d["justify-content"] == "center"
        assert d["align-items"] == "center"

    def test_text_styles(self):
        node = {
            "layout": {},
            "styles": {},
            "text": {
                "fontSize": 16,
                "fontFamily": "Inter",
                "fontWeight": 600,
                "lineHeight": 24,
                "letterSpacing": 0.5,
                "textAlign": "CENTER",
                "color": "#333",
            },
        }
        d = _style_dict(node)
        assert d["font-size"] == "16px"
        assert d["font-family"] == "Inter"
        assert d["font-weight"] == "600"
        assert d["color"] == "#333"

    def test_border(self):
        node = {
            "layout": {},
            "styles": {"border": {"width": 2, "color": "#000", "style": "DASHED"}},
        }
        d = _style_dict(node)
        assert d["border"] == "2px dashed #000"

    def test_border_radius(self):
        node = {
            "layout": {},
            "styles": {"borderRadius": {"topLeft": 8, "topRight": 8, "bottomRight": 4, "bottomLeft": 4}},
        }
        d = _style_dict(node)
        assert d["border-radius"] == "8px 8px 4px 4px"

    def test_shadow(self):
        node = {
            "layout": {},
            "styles": {"shadow": [{"offsetX": 0, "offsetY": 2, "blur": 4, "spread": 0, "color": "rgba(0,0,0,0.1)"}]},
        }
        d = _style_dict(node)
        assert "box-shadow" in d


# ─── _collect_components ──────────────────────────────────────────────────────


class TestCollectComponents:
    def test_collects_component_type(self):
        tree = {
            "figmaName": "Page",
            "figmaType": "FRAME",
            "children": [
                {
                    "figmaName": "Button/Primary",
                    "figmaType": "COMPONENT",
                    "children": [],
                },
                {
                    "figmaName": "Button/Secondary",
                    "figmaType": "INSTANCE",
                    "children": [],
                },
            ],
        }
        comps = {}
        _collect_components(tree, comps)
        assert "Button" in comps
        assert "Primary" in comps["Button"].variants
        assert "Secondary" in comps["Button"].variants

    def test_slash_in_name_triggers_collection(self):
        tree = {
            "figmaName": "Card/Hover",
            "figmaType": "FRAME",
            "children": [],
        }
        comps = {}
        _collect_components(tree, comps)
        assert "Card" in comps


# ─── render functions ────────────────────────────────────────────────────────


RENDER_NODE = {
    "figmaName": "Container",
    "figmaType": "FRAME",
    "layout": {"width": 200, "height": 100},
    "styles": {},
    "children": [
        {
            "figmaName": "Title",
            "figmaType": "TEXT",
            "layout": {},
            "styles": {},
            "text": {"characters": "Hello World", "fontSize": 16, "fontWeight": 400},
            "children": [],
        },
    ],
}


class TestRenderHTML:
    def test_renders_div(self):
        sheet = StyleSheet(prefix="t")
        html = _render_html(RENDER_NODE, sheet)
        assert "<div" in html
        assert "Hello World" in html
        assert "<span" in html

    def test_text_node_uses_span(self):
        sheet = StyleSheet(prefix="t")
        text_node = RENDER_NODE["children"][0]
        html = _render_html(text_node, sheet)
        assert html.strip().startswith("<span")


class TestRenderReact:
    def test_renders_classname(self):
        sheet = StyleSheet(prefix="r")
        jsx = _render_react(RENDER_NODE, sheet)
        assert 'className="' in jsx
        assert "Hello World" in jsx

    def test_css_module_mode(self):
        sheet = StyleSheet(prefix="m")
        jsx = _render_react(RENDER_NODE, sheet, css_module=True)
        assert "styles['" in jsx


class TestRenderVue:
    def test_renders_class(self):
        sheet = StyleSheet(prefix="v")
        html = _render_vue(RENDER_NODE, sheet)
        assert 'class="' in html
        assert "Hello World" in html


class TestRenderFlutter:
    def test_renders_container(self):
        flutter = _render_flutter(RENDER_NODE)
        assert "Container(" in flutter

    def test_text_node(self):
        text_node = RENDER_NODE["children"][0]
        flutter = _render_flutter(text_node)
        assert "Text(" in flutter
        assert "Hello World" in flutter
        assert "TextStyle(" in flutter
