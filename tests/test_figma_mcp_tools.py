"""Tests for figma_mcp_tools — all Figma API calls mocked."""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

from airis_pdm.figma_mcp_tools import (
    FigmaMcpTools,
    _ok,
    _err,
    _count_layout_warnings,
)


# ─── helpers ────────────────────────────────────────────────────────────────


class TestOkErr:
    def test_ok(self):
        result = json.loads(_ok({"x": 1}))
        assert result["status"] == "ok"
        assert result["data"]["x"] == 1

    def test_err(self):
        result = json.loads(_err("boom"))
        assert result["status"] == "error"
        assert result["message"] == "boom"


# ─── _count_layout_warnings ────────────────────────────────────────────────


class TestCountLayoutWarnings:
    def test_none_node(self):
        assert _count_layout_warnings(None) == 0

    def test_no_warnings(self):
        node = {"children": [{"children": []}]}
        assert _count_layout_warnings(node) == 0

    def test_nested_warnings(self):
        node = {
            "_layoutWarning": "NO_AUTO_LAYOUT",
            "children": [
                {"_layoutWarning": "NO_AUTO_LAYOUT", "children": []},
                {"children": []},
            ],
        }
        assert _count_layout_warnings(node) == 2


# ─── fixtures ───────────────────────────────────────────────────────────────


SAMPLE_IR = {
    "figmaName": "Root",
    "figmaType": "FRAME",
    "layout": {"width": 400, "height": 300},
    "styles": {"backgroundColor": "#fff"},
    "children": [
        {
            "figmaName": "Title",
            "figmaType": "TEXT",
            "layout": {},
            "styles": {},
            "text": {"characters": "Hello", "fontSize": 16},
            "children": [],
        }
    ],
}

FIGMA_RAW_RESPONSE = {
    "nodes": {
        "1:2": {
            "document": {
                "name": "Root",
                "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 300},
                "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1, "a": 1}}],
                "children": [],
            }
        }
    }
}


def _make_tools():
    """Build FigmaMcpTools with fully mocked internals."""
    with patch("airis_pdm.figma_mcp_tools.FigmaAPIClient") as MockClient, \
         patch("airis_pdm.figma_mcp_tools.FigmaToIR") as MockIR, \
         patch("airis_pdm.figma_mcp_tools.IRDiffer") as MockDiffer:

        client_inst = MockClient.return_value
        ir_inst = MockIR.return_value
        differ_inst = MockDiffer.return_value

        tools = FigmaMcpTools(token="fake-token")
        return tools, client_inst, ir_inst, differ_inst


# ─── get_figma_ir ───────────────────────────────────────────────────────────


class TestGetFigmaIR:
    def test_success(self):
        tools, client, ir_conv, _ = _make_tools()
        client.get_file_nodes.return_value = FIGMA_RAW_RESPONSE
        ir_conv.convert.return_value = SAMPLE_IR

        result = json.loads(tools.get_figma_ir("abc123", "1:2"))
        assert result["status"] == "ok"
        assert result["data"]["figmaName"] == "Root"

    def test_node_not_found(self):
        tools, client, _, _ = _make_tools()
        client.get_file_nodes.return_value = {"nodes": {"1:2": {}}}

        result = json.loads(tools.get_figma_ir("abc123", "1:2"))
        assert result["status"] == "error"
        assert "找不到節點" in result["message"]

    def test_api_exception(self):
        tools, client, _, _ = _make_tools()
        client.get_file_nodes.side_effect = RuntimeError("network error")

        result = json.loads(tools.get_figma_ir("abc123", "1:2"))
        assert result["status"] == "error"
        assert "network error" in result["message"]


# ─── diff_ir_with_snapshot ──────────────────────────────────────────────────


class TestDiffIRWithSnapshot:
    def test_no_snapshot(self, tmp_path):
        tools, client, ir_conv, _ = _make_tools()
        tools._snapshot_dir = str(tmp_path / "missing")
        client.get_file_nodes.return_value = FIGMA_RAW_RESPONSE
        ir_conv.convert.return_value = SAMPLE_IR

        result = json.loads(tools.diff_ir_with_snapshot("abc123", "1:2"))
        assert result["status"] == "error"
        assert "快照不存在" in result["message"]

    def test_has_changes(self, tmp_path):
        tools, client, ir_conv, differ = _make_tools()
        tools._snapshot_dir = str(tmp_path)
        client.get_file_nodes.return_value = FIGMA_RAW_RESPONSE
        ir_conv.convert.return_value = SAMPLE_IR
        differ.diff.return_value = {"Root": {"styles.backgroundColor": {"before": "#fff", "after": "#000"}}}

        # Create snapshot
        snap_dir = tmp_path / "1_2"
        snap_dir.mkdir()
        (snap_dir / "ir.json").write_text(json.dumps(SAMPLE_IR))

        result = json.loads(tools.diff_ir_with_snapshot("abc123", "1:2"))
        assert result["status"] == "ok"
        assert result["data"]["hasChanges"] is True

    def test_no_changes(self, tmp_path):
        tools, client, ir_conv, differ = _make_tools()
        tools._snapshot_dir = str(tmp_path)
        client.get_file_nodes.return_value = FIGMA_RAW_RESPONSE
        ir_conv.convert.return_value = SAMPLE_IR
        differ.diff.return_value = {}

        snap_dir = tmp_path / "1_2"
        snap_dir.mkdir()
        (snap_dir / "ir.json").write_text(json.dumps(SAMPLE_IR))

        result = json.loads(tools.diff_ir_with_snapshot("abc123", "1:2"))
        assert result["status"] == "ok"
        assert result["data"]["hasChanges"] is False

    def test_node_not_found(self):
        tools, client, _, _ = _make_tools()
        client.get_file_nodes.return_value = {"nodes": {"1:2": {}}}

        result = json.loads(tools.diff_ir_with_snapshot("abc123", "1:2"))
        assert result["status"] == "error"


# ─── get_design_tokens ──────────────────────────────────────────────────────


class TestGetDesignTokens:
    def test_success(self):
        tools, client, ir_conv, _ = _make_tools()
        client.get_file_nodes.return_value = FIGMA_RAW_RESPONSE
        ir_conv.convert.return_value = SAMPLE_IR

        result = json.loads(tools.get_design_tokens("abc123", "1:2"))
        assert result["status"] == "ok"
        assert "colors" in result["data"]

    def test_node_not_found(self):
        tools, client, _, _ = _make_tools()
        client.get_file_nodes.return_value = {"nodes": {"1:2": {}}}

        result = json.loads(tools.get_design_tokens("abc123", "1:2"))
        assert result["status"] == "error"


# ─── get_ir_completeness ───────────────────────────────────────────────────


class TestGetIRCompleteness:
    def test_success_high_score(self):
        tools, client, ir_conv, _ = _make_tools()
        client.get_file_nodes.return_value = FIGMA_RAW_RESPONSE
        ir_conv.convert.return_value = SAMPLE_IR

        result = json.loads(tools.get_ir_completeness("abc123", "1:2"))
        assert result["status"] == "ok"
        assert "score" in result["data"]
        assert "summary" in result["data"]
        assert result["data"]["hasStyles"] is True
        assert result["data"]["hasText"] is True

    def test_node_not_found(self):
        tools, client, _, _ = _make_tools()
        client.get_file_nodes.return_value = {"nodes": {"1:2": {}}}

        result = json.loads(tools.get_ir_completeness("abc123", "1:2"))
        assert result["status"] == "error"


# ─── list_snapshots ─────────────────────────────────────────────────────────


class TestListSnapshots:
    def test_empty_dir(self, tmp_path):
        tools, _, _, _ = _make_tools()
        tools._snapshot_dir = str(tmp_path)

        result = json.loads(tools.list_snapshots())
        assert result["status"] == "ok"
        assert result["data"]["snapshots"] == []

    def test_missing_dir(self, tmp_path):
        tools, _, _, _ = _make_tools()
        tools._snapshot_dir = str(tmp_path / "nonexistent")

        result = json.loads(tools.list_snapshots())
        assert result["status"] == "ok"
        assert result["data"]["snapshots"] == []

    def test_with_snapshot(self, tmp_path):
        tools, _, _, _ = _make_tools()
        tools._snapshot_dir = str(tmp_path)

        snap_dir = tmp_path / "1_2"
        snap_dir.mkdir()
        (snap_dir / "ir.json").write_text("{}")

        result = json.loads(tools.list_snapshots())
        assert result["status"] == "ok"
        snaps = result["data"]["snapshots"]
        assert len(snaps) == 1
        assert snaps[0]["nodeId"] == "1:2"
        assert snaps[0]["hasIr"] is True
        assert snaps[0]["hasScreenshot"] is False

    def test_with_screenshot(self, tmp_path):
        tools, _, _, _ = _make_tools()
        tools._snapshot_dir = str(tmp_path)

        snap_dir = tmp_path / "3_4"
        snap_dir.mkdir()
        (snap_dir / "screenshot.png").write_bytes(b"fake")

        result = json.loads(tools.list_snapshots())
        snaps = result["data"]["snapshots"]
        assert snaps[0]["hasScreenshot"] is True
        assert snaps[0]["hasIr"] is False
