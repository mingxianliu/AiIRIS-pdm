"""figma_console_ws 基本檢查（不需真連 Figma）。"""

import asyncio
import json
import logging
from pathlib import Path

import pytest


def test_bridge_script_bundled():
    from airis_pdm.figma_console_ws import bridge_script_path

    p: Path = bridge_script_path()
    assert p.name == "figma_console_bridge.js"
    assert p.exists()
    assert "FIGMA" in p.read_text(encoding="utf-8", errors="replace").upper()


class _FakeConn:
    def __init__(self, recv_result=None, recv_error=None):
        self.recv_result = recv_result
        self.recv_error = recv_error
        self.sent = []

    async def send(self, payload: str):
        self.sent.append(json.loads(payload))

    async def recv(self):
        if self.recv_error:
            raise self.recv_error
        return self.recv_result


class _FakeConnectCtx:
    def __init__(self, conn: _FakeConn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_request_sync_retries_timeout_then_succeeds(monkeypatch):
    from airis_pdm import figma_console_ws as mod

    attempts = []
    sleeps = []

    def fake_connect(uri: str, open_timeout: float):
        attempts.append((uri, open_timeout))
        if len(attempts) == 1:
            return _FakeConnectCtx(_FakeConn(recv_error=asyncio.TimeoutError("recv timeout")))
        return _FakeConnectCtx(_FakeConn(recv_result=json.dumps({"id": 1, "result": {"ok": True}})))

    async def fake_sleep(delay: float):
        sleeps.append(delay)

    monkeypatch.setattr(mod, "_require_ws_libs", lambda: None)
    monkeypatch.setattr(mod, "ws_connect", fake_connect)
    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    result = mod.request_sync("getNode", {"nodeId": "1:1"}, timeout=1, retries=1, retry_backoff_s=0.5)
    assert result == {"ok": True}
    assert len(attempts) == 2
    assert sleeps == [0.5]


def test_request_sync_retries_oserror_then_succeeds(monkeypatch):
    from airis_pdm import figma_console_ws as mod

    calls = {"count": 0}

    def fake_connect(uri: str, open_timeout: float):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("connection reset by peer")
        return _FakeConnectCtx(_FakeConn(recv_result=json.dumps({"id": 1, "result": {"items": []}})))

    async def fake_sleep(delay: float):
        return None

    monkeypatch.setattr(mod, "_require_ws_libs", lambda: None)
    monkeypatch.setattr(mod, "ws_connect", fake_connect)
    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    result = mod.request_sync("searchNodes", {"pattern": "[Page]"}, timeout=1, retries=2, retry_backoff_s=0.1)
    assert result == {"items": []}
    assert calls["count"] == 2


def test_request_sync_does_not_retry_response_error(monkeypatch):
    from airis_pdm import figma_console_ws as mod

    calls = {"count": 0}

    def fake_connect(uri: str, open_timeout: float):
        calls["count"] += 1
        payload = json.dumps({"id": 1, "error": {"message": "method not supported"}})
        return _FakeConnectCtx(_FakeConn(recv_result=payload))

    async def fake_sleep(delay: float):
        raise AssertionError("response errors must not back off")

    monkeypatch.setattr(mod, "_require_ws_libs", lambda: None)
    monkeypatch.setattr(mod, "ws_connect", fake_connect)
    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    with pytest.raises(mod.FigmaConsoleResponseError, match="method not supported"):
        mod.request_sync("unknownMethod", {}, timeout=1, retries=3, retry_backoff_s=0.1)
    assert calls["count"] == 1


def test_request_sync_raises_retryable_error_after_exhausting_retries(monkeypatch):
    from airis_pdm import figma_console_ws as mod

    def fake_connect(uri: str, open_timeout: float):
        raise ConnectionError("temporary network issue")

    async def fake_sleep(delay: float):
        return None

    monkeypatch.setattr(mod, "_require_ws_libs", lambda: None)
    monkeypatch.setattr(mod, "ws_connect", fake_connect)
    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    with pytest.raises(mod.FigmaConsoleRetryableError, match="ping failed on attempt 2"):
        mod.request_sync("ping", {}, timeout=1, retries=1, retry_backoff_s=0.1)


def test_request_sync_verbose_logs_trace_and_timing(monkeypatch, caplog):
    from airis_pdm import figma_console_ws as mod

    def fake_connect(uri: str, open_timeout: float):
        return _FakeConnectCtx(_FakeConn(recv_result=json.dumps({"id": 1, "result": {"ok": True}})))

    monkeypatch.setattr(mod, "_require_ws_libs", lambda: None)
    monkeypatch.setattr(mod, "ws_connect", fake_connect)

    with caplog.at_level(logging.INFO):
        result = mod.request_sync(
            "getNode",
            {"nodeId": "1:1"},
            timeout=1,
            trace_id="trace-123",
            verbose=True,
        )

    assert result == {"ok": True}
    assert "trace_id=trace-123" in caplog.text
    assert "elapsed_ms=" in caplog.text
