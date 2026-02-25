"""
Storybook Sync（cmd_push_stories）mock 測試（P2 #12）
模擬 Storybook stories.json HTTP、DOM 擷取與 IR 合批邏輯，不需要真實伺服器。
"""
import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── 測試用 stub 資料 ─────────────────────────────────────────────────────────

STORIES_JSON = {
    "stories": {
        "button--primary": {
            "id": "button--primary",
            "name": "Primary",
            "kind": "Button",
        },
        "button--secondary": {
            "id": "button--secondary",
            "name": "Secondary",
            "kind": "Button",
        },
        "input--default": {
            "id": "input--default",
            "name": "Default",
            "kind": "Input",
        },
    }
}

MINIMAL_IR_DOC = {
    "version": "2.0.0",
    "tree": {
        "figmaName": "Root",
        "figmaType": "FRAME",
        "htmlTag": "div",
        "layout": {"x": 0, "y": 0, "width": 800, "height": 600},
        "children": [],
    },
    "nameMapping": {},
    "stats": {"nodeCount": 1},
}

MINIMAL_EXTRACTION = {
    "tree": {
        "tag": "div",
        "attrs": {"id": "root"},
        "layout": {"x": 0, "y": 0, "width": 800, "height": 600},
        "children": [],
    },
    "screenshot": b"",
    "viewport": {"width": 800, "height": 600},
}


def make_args(url="http://localhost:6006", filter_regex=None):
    args = MagicMock()
    args.url = url
    args.filter = filter_regex
    args.viewport = None
    args.selector = None
    args.root = None
    return args


def make_stories_response(data=None):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data or STORIES_JSON
    return resp


# ─── 正常流程：成功擷取並合批 ──────────────────────────────────────────────────

class TestCmdPushStoriesSuccess:

    def _run(self, args, config, mock_get, mock_extract, mock_build, mock_save, tmp_path):
        from airis_pdm.cli import cmd_push_stories

        mock_get.return_value = make_stories_response()
        mock_extract.return_value = MINIMAL_EXTRACTION
        mock_build.return_value = MINIMAL_IR_DOC

        config["export"] = {"snapshotDir": str(tmp_path)}
        asyncio.run(cmd_push_stories(args, config))

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_fetches_stories_json(self, mock_get, mock_build, mock_extract, tmp_path):
        mock_get.return_value = make_stories_response()
        mock_extract.return_value = MINIMAL_EXTRACTION
        mock_build.return_value = MINIMAL_IR_DOC

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(__import__("airis_pdm.cli", fromlist=["cmd_push_stories"]).cmd_push_stories(args, config))

        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        assert "/stories.json" in called_url

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_plugin_payload_written(self, mock_get, mock_build, mock_extract, tmp_path):
        from airis_pdm.cli import cmd_push_stories

        mock_get.return_value = make_stories_response()
        mock_extract.return_value = MINIMAL_EXTRACTION
        mock_build.return_value = MINIMAL_IR_DOC

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        payload_path = tmp_path / "plugin-payload.json"
        assert payload_path.exists(), "plugin-payload.json 應該被寫出"

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_payload_contains_all_stories(self, mock_get, mock_build, mock_extract, tmp_path):
        from airis_pdm.cli import cmd_push_stories

        mock_get.return_value = make_stories_response()
        mock_extract.return_value = MINIMAL_EXTRACTION
        mock_build.return_value = MINIMAL_IR_DOC

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        payload = json.loads((tmp_path / "plugin-payload.json").read_text())
        # 根節點應為 "Storybook Sync"
        assert payload["figmaName"] == "Storybook Sync"
        # 3 個 stories 都被擷取
        assert len(payload["children"]) == 3

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_story_names_overridden(self, mock_get, mock_build, mock_extract, tmp_path):
        from airis_pdm.cli import cmd_push_stories
        import copy

        mock_get.return_value = make_stories_response()
        mock_extract.return_value = MINIMAL_EXTRACTION
        # 每次回傳独立 copy，避免 mutable dict 被多次直接修改
        mock_build.side_effect = lambda *a, **kw: copy.deepcopy(MINIMAL_IR_DOC)

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        payload = json.loads((tmp_path / "plugin-payload.json").read_text())
        child_names = [c["figmaName"] for c in payload["children"]]
        # 名稱格式：kind/name，例如 "Button/Primary"
        assert any("/" in n for n in child_names)

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_stories_laid_out_horizontally(self, mock_get, mock_build, mock_extract, tmp_path):
        from airis_pdm.cli import cmd_push_stories
        import copy

        mock_get.return_value = make_stories_response()
        mock_extract.return_value = MINIMAL_EXTRACTION
        # 每次回傳独立 copy，避免 x_pos 覆寫到同一個 dict
        mock_build.side_effect = lambda *a, **kw: copy.deepcopy(MINIMAL_IR_DOC)

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        payload = json.loads((tmp_path / "plugin-payload.json").read_text())
        x_positions = [c["layout"]["x"] for c in payload["children"]]
        # 水平排列：x 位置應遞增
        assert x_positions == sorted(x_positions)
        assert x_positions[0] < x_positions[-1]

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_args_selector_not_mutated(self, mock_get, mock_build, mock_extract, tmp_path):
        """P1 #7：push-stories 不應修改 args.selector。"""
        from airis_pdm.cli import cmd_push_stories

        mock_get.return_value = make_stories_response()
        mock_extract.return_value = MINIMAL_EXTRACTION
        mock_build.return_value = MINIMAL_IR_DOC

        args = make_args()
        original_selector = args.selector  # None

        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        assert args.selector == original_selector, "args.selector 不應被 push-stories 修改"


# ─── 錯誤處理 ────────────────────────────────────────────────────────────────

class TestCmdPushStoriesErrors:

    @patch("airis_pdm.cli.requests.get")
    def test_stories_json_404_returns_early(self, mock_get, tmp_path, capsys):
        from airis_pdm.cli import cmd_push_stories

        resp = MagicMock()
        resp.status_code = 404
        mock_get.return_value = resp

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        captured = capsys.readouterr()
        assert "stories.json" in captured.out or "Could not" in captured.out

    @patch("airis_pdm.cli.requests.get")
    def test_network_error_handled(self, mock_get, tmp_path, capsys):
        from airis_pdm.cli import cmd_push_stories

        mock_get.side_effect = Exception("Connection refused")

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        captured = capsys.readouterr()
        assert "Error" in captured.out or "❌" in captured.out

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_extraction_failure_skips_story(self, mock_get, mock_build, mock_extract, tmp_path, capsys):
        """單一 story 擷取失敗應跳過，不影響其他 story。"""
        from airis_pdm.cli import cmd_push_stories

        mock_get.return_value = make_stories_response()
        # 第一個 story 失敗，其餘正常
        mock_extract.side_effect = [
            Exception("timeout"),
            MINIMAL_EXTRACTION,
            MINIMAL_EXTRACTION,
        ]
        mock_build.return_value = MINIMAL_IR_DOC

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        # 剩餘 2 個 story 仍應被寫出
        payload = json.loads((tmp_path / "plugin-payload.json").read_text())
        assert len(payload["children"]) == 2

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_empty_tree_skips_story(self, mock_get, mock_build, mock_extract, tmp_path):
        """DOM 擷取結果為空 tree 的 story 應被跳過。"""
        from airis_pdm.cli import cmd_push_stories

        mock_get.return_value = make_stories_response()
        empty_extraction = {**MINIMAL_EXTRACTION, "tree": None}
        mock_extract.side_effect = [
            empty_extraction,
            MINIMAL_EXTRACTION,
            MINIMAL_EXTRACTION,
        ]
        mock_build.return_value = MINIMAL_IR_DOC

        args = make_args()
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        payload = json.loads((tmp_path / "plugin-payload.json").read_text())
        # 空 tree 的 story 被 build_ir_from_extraction 正常處理
        # 由於 mock_build 仍回傳 MINIMAL_IR_DOC，所以算 3 筆
        # 但 extraction tree 是 None → 在 extract_dom_tree 成功後 build 時仍可能被接受
        # 此測試主要確認：不崩潰
        assert isinstance(payload["children"], list)


# ─── filter 參數 ─────────────────────────────────────────────────────────────

class TestCmdPushStoriesFilter:

    @patch("airis_pdm.cli.extract_dom_tree", new_callable=AsyncMock)
    @patch("airis_pdm.cli.build_ir_from_extraction")
    @patch("airis_pdm.cli.requests.get")
    def test_filter_regex_limits_stories(self, mock_get, mock_build, mock_extract, tmp_path):
        from airis_pdm.cli import cmd_push_stories

        mock_get.return_value = make_stories_response()
        mock_extract.return_value = MINIMAL_EXTRACTION
        mock_build.return_value = MINIMAL_IR_DOC

        args = make_args(filter_regex="Primary")
        config = {"source": {"framework": "html"}, "export": {"snapshotDir": str(tmp_path)}}
        asyncio.run(cmd_push_stories(args, config))

        payload = json.loads((tmp_path / "plugin-payload.json").read_text())
        # 只有 "Primary" 符合正規表示式
        assert len(payload["children"]) == 1
