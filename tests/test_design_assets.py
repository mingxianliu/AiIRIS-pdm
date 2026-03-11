"""Tests for design_assets module."""

import json
import os
import pytest

from airis_pdm.design_assets import (
    write_erslice_manifest,
    write_completeness,
    extract_design_tokens_from_ir,
    _count_nodes,
    _has_any_styles,
    _has_any_text,
)


# ─── Helper IR fixtures ────────────────────────────────────────────────────


SIMPLE_IR = {
    "source": {"framework": "vue"},
    "viewport": {"width": 1440, "height": 900},
    "tree": {
        "figmaName": "Root",
        "styles": {"backgroundColor": "#fff"},
        "children": [
            {
                "figmaName": "Title",
                "styles": {"color": "#333"},
                "text": {"characters": "Hello", "fontSize": 24, "fontFamily": "Inter", "color": "#333"},
                "children": [],
            },
            {
                "figmaName": "Spacer",
                "styles": {},
                "children": [],
            },
        ],
    },
}

EMPTY_IR = {"tree": {}}


# ─── _count_nodes ────────────────────────────────────────────────────────────


class TestCountNodes:
    def test_single_node(self):
        assert _count_nodes({"children": []}) == 1

    def test_nested(self):
        assert _count_nodes(SIMPLE_IR["tree"]) == 3  # Root + Title + Spacer

    def test_none(self):
        assert _count_nodes(None) == 0


# ─── _has_any_styles ─────────────────────────────────────────────────────────


class TestHasAnyStyles:
    def test_has_styles(self):
        assert _has_any_styles(SIMPLE_IR["tree"]) is True

    def test_no_styles(self):
        assert _has_any_styles({"styles": {}, "children": []}) is False


# ─── _has_any_text ───────────────────────────────────────────────────────────


class TestHasAnyText:
    def test_has_text(self):
        assert _has_any_text(SIMPLE_IR["tree"]) is True

    def test_no_text(self):
        assert _has_any_text({"text": {}, "children": []}) is False
        assert _has_any_text({"children": []}) is False


# ─── write_erslice_manifest ──────────────────────────────────────────────────


class TestWriteErsliceManifest:
    def test_creates_manifest(self, tmp_path):
        out_dir = str(tmp_path / "assets")
        path = write_erslice_manifest(out_dir, "login", "login-page", SIMPLE_IR, source_url="https://figma.com/xxx")
        assert os.path.isfile(path)
        data = json.loads(open(path).read())
        assert data["module"] == "login"
        assert data["page"] == "login-page"
        assert data["source"] == "airis_pdm"
        assert data["framework"] == "vue"
        assert data["nodeCount"] == 3

    def test_creates_directory(self, tmp_path):
        out_dir = str(tmp_path / "nested" / "deep" / "assets")
        path = write_erslice_manifest(out_dir, "m", "p", SIMPLE_IR)
        assert os.path.isfile(path)


# ─── write_completeness ─────────────────────────────────────────────────────


class TestWriteCompleteness:
    def test_creates_completeness(self, tmp_path):
        out_dir = str(tmp_path / "assets")
        path = write_completeness(out_dir, SIMPLE_IR, has_screenshot=True)
        assert os.path.isfile(path)
        data = json.loads(open(path).read())
        assert "score" in data
        assert data["hasStyles"] is True
        assert data["hasText"] is True
        assert data["hasScreenshot"] is True
        assert data["nodeCount"] == 3

    def test_empty_ir_low_score(self, tmp_path):
        out_dir = str(tmp_path / "assets")
        write_completeness(out_dir, EMPTY_IR, has_screenshot=False)
        data = json.loads(open(str(tmp_path / "assets" / "completeness.json")).read())
        assert data["score"] <= 10


# ─── extract_design_tokens_from_ir ───────────────────────────────────────────


class TestExtractDesignTokensFromIR:
    def test_extracts_colors(self):
        tokens = extract_design_tokens_from_ir(SIMPLE_IR["tree"])
        assert "#fff" in tokens["colors"]
        assert "#333" in tokens["colors"]

    def test_extracts_font_sizes(self):
        tokens = extract_design_tokens_from_ir(SIMPLE_IR["tree"])
        assert "24" in tokens["fontSizes"]

    def test_extracts_font_families(self):
        tokens = extract_design_tokens_from_ir(SIMPLE_IR["tree"])
        assert "Inter" in tokens["fontFamilies"]

    def test_no_duplicates(self):
        tokens = extract_design_tokens_from_ir(SIMPLE_IR["tree"])
        assert len(tokens["colors"]) == len(set(tokens["colors"]))

    def test_empty_tree(self):
        tokens = extract_design_tokens_from_ir({})
        assert tokens["colors"] == []
        assert tokens["fontSizes"] == []
        assert tokens["fontFamilies"] == []
