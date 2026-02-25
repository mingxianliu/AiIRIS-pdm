"""
Watch Mode / ChangeHandler debounce 單元測試（P2 #11）
不需要真實檔案系統事件，用 mock event 物件測試防抖與 loop 排程邏輯。
"""
import asyncio
import time
import threading
import pytest
from unittest.mock import MagicMock, patch, call

from airis_pdm.cli import ChangeHandler, _WATCHED_EXTENSIONS


# ─── helper: 建立假 FileModifiedEvent ────────────────────────────────────────

def make_event(src_path: str, is_directory: bool = False):
    ev = MagicMock()
    ev.is_directory = is_directory
    ev.src_path = src_path
    return ev


# ─── ChangeHandler.on_modified 過濾邏輯 ──────────────────────────────────────

class TestChangeHandlerFilter:
    """測試 on_modified 的過濾條件：目錄、副檔名、callback 呼叫。"""

    def setup_method(self):
        self.loop = asyncio.new_event_loop()
        self.callback_called = 0

        async def dummy_callback():
            self.callback_called += 1

        self.handler = ChangeHandler(dummy_callback, self.loop, debounce=0.0)

    def teardown_method(self):
        self.loop.close()

    def test_directory_event_ignored(self):
        ev = make_event("/src/components/", is_directory=True)
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            self.handler.on_modified(ev)
            mock_run.assert_not_called()

    def test_non_watched_extension_ignored(self):
        for ext in [".png", ".md", ".json", ".lock", ".pyc"]:
            ev = make_event(f"/src/file{ext}")
            with patch("asyncio.run_coroutine_threadsafe") as mock_run:
                self.handler.on_modified(ev)
                mock_run.assert_not_called(), f"{ext} 應被忽略"

    def test_watched_extensions_trigger_callback(self):
        for ext in _WATCHED_EXTENSIONS:
            ev = make_event(f"/src/Button{ext}")
            with patch("asyncio.run_coroutine_threadsafe") as mock_run:
                self.handler.last_trigger = 0  # 重置 debounce
                self.handler.on_modified(ev)
                mock_run.assert_called_once(), f"{ext} 應觸發 callback"

    def test_callback_receives_correct_loop(self):
        ev = make_event("/src/App.vue")
        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            self.handler.on_modified(ev)
            _, kwargs_or_args = mock_run.call_args[0], mock_run.call_args[1] or {}
            # 第二個位置參數是 loop
            assert mock_run.call_args[0][1] is self.loop


# ─── ChangeHandler debounce 邏輯 ─────────────────────────────────────────────

class TestChangeHandlerDebounce:
    """測試防抖：短時間內重複觸發只呼叫一次 callback。"""

    def setup_method(self):
        self.loop = asyncio.new_event_loop()

        async def dummy():
            pass

        self.handler = ChangeHandler(dummy, self.loop, debounce=0.5)

    def teardown_method(self):
        self.loop.close()

    def test_debounce_blocks_rapid_events(self):
        ev = make_event("/src/App.vue")
        call_count = 0

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            # 第一次觸發
            self.handler.on_modified(ev)
            # 立即再觸發（在 debounce 視窗內）
            self.handler.on_modified(ev)
            self.handler.on_modified(ev)
            # 只有第一次應該被送進 loop
            assert mock_run.call_count == 1

    def test_debounce_allows_event_after_window(self):
        ev = make_event("/src/App.vue")

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            # 第一次
            self.handler.on_modified(ev)
            assert mock_run.call_count == 1

            # 模擬時間過了超過 debounce 視窗
            self.handler.last_trigger = time.time() - 1.0

            # 第二次（應該通過）
            self.handler.on_modified(ev)
            assert mock_run.call_count == 2

    def test_debounce_timestamp_updated(self):
        ev = make_event("/src/App.vue")
        before = time.time() - 0.01

        with patch("asyncio.run_coroutine_threadsafe"):
            self.handler.on_modified(ev)
            assert self.handler.last_trigger >= before


# ─── _WATCHED_EXTENSIONS 常數驗證 ────────────────────────────────────────────

def test_watched_extensions_includes_common_types():
    for ext in (".vue", ".tsx", ".jsx", ".ts", ".js", ".css", ".scss", ".html"):
        assert ext in _WATCHED_EXTENSIONS, f"{ext} 應在 _WATCHED_EXTENSIONS"


def test_watched_extensions_excludes_binary_types():
    for ext in (".png", ".jpg", ".woff", ".mp4", ".json"):
        assert ext not in _WATCHED_EXTENSIONS, f"{ext} 不應在 _WATCHED_EXTENSIONS"
