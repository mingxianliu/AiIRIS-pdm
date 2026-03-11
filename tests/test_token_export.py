"""Tests for token_export module."""

import json
import os
import pytest

from airis_pdm.token_export import (
    _normalize_color,
    extract_tokens_from_ir,
    tokens_to_css,
    export_tokens,
)


# ─── _normalize_color ───────────────────────────────────────────────────────


class TestNormalizeColor:
    def test_string_passthrough(self):
        assert _normalize_color("rgba(0,0,0,1)") == "rgba(0,0,0,1)"

    def test_empty_string_returns_none(self):
        assert _normalize_color("") is None
        assert _normalize_color("   ") is None

    def test_none_input(self):
        assert _normalize_color(None) is None

    def test_dict_float_0_to_1(self):
        result = _normalize_color({"r": 1.0, "g": 0.5, "b": 0.0, "a": 0.8})
        assert result == "rgba(255,127,0,0.8)"

    def test_dict_int_255(self):
        result = _normalize_color({"r": 255, "g": 128, "b": 0, "a": 1})
        assert result == "rgba(255,128,0,1)"

    def test_dict_missing_alpha_defaults_1(self):
        result = _normalize_color({"r": 0.0, "g": 0.0, "b": 0.0})
        assert result == "rgba(0,0,0,1)"

    def test_unsupported_type_returns_none(self):
        assert _normalize_color(42) is None
        assert _normalize_color([1, 2, 3]) is None


# ─── extract_tokens_from_ir ──────────────────────────────────────────────────


SAMPLE_IR = {
    "tree": {
        "figmaName": "Root",
        "styles": {
            "fills": [{"type": "SOLID", "color": "rgba(255,0,0,1)"}],
            "backgroundColor": "#f5f5f5",
        },
        "text": None,
        "autoLayout": {"spacing": 16},
        "children": [
            {
                "figmaName": "Heading",
                "styles": {},
                "text": {
                    "color": "rgba(0,0,0,1)",
                    "fontSize": 24,
                    "fontFamily": "Inter",
                    "fontWeight": 700,
                    "lineHeight": 32,
                },
                "children": [],
            },
            {
                "figmaName": "Body",
                "styles": {
                    "fills": [{"type": "SOLID", "color": "rgba(255,0,0,1)"}],
                },
                "text": {
                    "color": "rgba(51,51,51,1)",
                    "fontSize": 14,
                    "fontFamily": "Inter",
                    "fontWeight": 400,
                    "lineHeight": 20,
                },
                "autoLayout": {"spacing": 8},
                "children": [],
            },
        ],
    }
}


class TestExtractTokensFromIR:
    def test_extracts_colors(self):
        tokens = extract_tokens_from_ir(SAMPLE_IR)
        assert "rgba(255,0,0,1)" in tokens["colors"]
        assert "#f5f5f5" in tokens["colors"]

    def test_extracts_font_sizes_sorted(self):
        tokens = extract_tokens_from_ir(SAMPLE_IR)
        assert tokens["typography"]["fontSizes"] == [14, 24]

    def test_extracts_font_families(self):
        tokens = extract_tokens_from_ir(SAMPLE_IR)
        assert "Inter" in tokens["typography"]["fontFamilies"]

    def test_extracts_font_weights_sorted(self):
        tokens = extract_tokens_from_ir(SAMPLE_IR)
        assert tokens["typography"]["fontWeights"] == [400, 700]

    def test_extracts_spacing_sorted(self):
        tokens = extract_tokens_from_ir(SAMPLE_IR)
        assert tokens["spacing"] == [8, 16]

    def test_empty_ir(self):
        tokens = extract_tokens_from_ir({})
        assert tokens["colors"] == []
        assert tokens["spacing"] == []

    def test_bare_node_no_tree_key(self):
        """IR without 'tree' key but with children should still work."""
        bare = {
            "styles": {"fills": [{"type": "SOLID", "color": "#000"}]},
            "children": [],
        }
        tokens = extract_tokens_from_ir(bare)
        assert "#000" in tokens["colors"]

    def test_no_duplicates(self):
        tokens = extract_tokens_from_ir(SAMPLE_IR)
        assert len(tokens["colors"]) == len(set(tokens["colors"]))


# ─── tokens_to_css ──────────────────────────────────────────────────────────


class TestTokensToCss:
    def test_basic_output(self):
        tokens = {
            "colors": ["#fff", "#000"],
            "typography": {"fontSizes": [14, 24], "fontFamilies": ["Inter"]},
            "spacing": [8, 16],
        }
        css = tokens_to_css(tokens)
        assert ":root {" in css
        assert "--token-color-1: #fff;" in css
        assert "--token-font-size-1: 14px;" in css
        assert '--token-font-family-1: "Inter";' in css
        assert "--token-spacing-1: 8px;" in css

    def test_custom_prefix(self):
        tokens = {"colors": ["red"], "typography": {}, "spacing": []}
        css = tokens_to_css(tokens, prefix="--ds")
        assert "--ds-color-1: red;" in css

    def test_empty_tokens(self):
        tokens = {"colors": [], "typography": {}, "spacing": []}
        css = tokens_to_css(tokens)
        assert ":root {" in css
        assert "}" in css


# ─── export_tokens (integration) ────────────────────────────────────────────


class TestExportTokens:
    def test_export_json(self, tmp_path):
        ir_doc = SAMPLE_IR
        ir_file = tmp_path / "ir.json"
        ir_file.write_text(json.dumps(ir_doc), encoding="utf-8")
        out_file = str(tmp_path / "tokens.json")

        result = export_tokens(str(ir_file), out_file, format="json")
        assert os.path.isfile(result)
        data = json.loads(open(result).read())
        assert "colors" in data
        assert "typography" in data

    def test_export_css(self, tmp_path):
        ir_doc = SAMPLE_IR
        ir_file = tmp_path / "ir.json"
        ir_file.write_text(json.dumps(ir_doc), encoding="utf-8")
        out_file = str(tmp_path / "tokens.css")

        result = export_tokens(str(ir_file), out_file, format="css")
        content = open(result).read()
        assert "--token-color-" in content

    def test_export_from_directory(self, tmp_path):
        ir_doc = SAMPLE_IR
        ir_file = tmp_path / "figma-import-payload.json"
        ir_file.write_text(json.dumps(ir_doc), encoding="utf-8")
        out_file = str(tmp_path / "out" / "tokens.json")

        result = export_tokens(str(tmp_path), out_file)
        assert os.path.isfile(result)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            export_tokens(str(tmp_path / "nonexistent.json"), "out.json")
