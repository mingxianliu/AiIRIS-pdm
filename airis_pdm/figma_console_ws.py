"""
Figma Desktop「Console Bridge」WebSocket 代理（純 Python）

對齊原 FigmAI / figma-console-mcp 的轉發語意：Figma 內 bridge（role=plugin）與
本機工具（role=client）以 JSON 溝通，無需 Node/TypeScript 長服務。

Bridge 腳本：airis_pdm/assets/figma_console_bridge.js（由 aipdm figma-console bridge-path 取得路徑）
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

log = logging.getLogger(__name__)

try:
    from websockets.asyncio.server import serve as ws_serve
    from websockets.asyncio.client import connect as ws_connect
except ImportError:  # pragma: no cover
    ws_serve = None
    ws_connect = None


def _require_ws_libs() -> None:
    if ws_serve is None or ws_connect is None:
        raise ImportError(
            "需要安裝 websockets：pip install 'airis-pdm[figma-console]' 或 pip install websockets>=12"
        )


def bridge_script_path() -> Path:
    """內建 Figma Console 用 bridge.js 的絕對路徑。"""
    return Path(__file__).resolve().parent / "assets" / "figma_console_bridge.js"


def _decode_msg(raw: Any) -> str:
    if isinstance(raw, (bytes, bytearray)):
        return raw.decode("utf-8")
    return str(raw)


class FigmaConsoleError(RuntimeError):
    """Base exception for figma-console request failures."""


class FigmaConsoleRetryableError(FigmaConsoleError):
    """Raised for timeout / transport failures that may succeed on retry."""


class FigmaConsoleResponseError(FigmaConsoleError):
    """Raised when the server returns an application-level error."""


def _normalize_retryable_error(exc: Exception, *, method: str, attempt: int) -> FigmaConsoleRetryableError:
    if isinstance(exc, FigmaConsoleRetryableError):
        return exc
    return FigmaConsoleRetryableError(f"{method} failed on attempt {attempt}: {exc}")


def _normalize_response_error(err: Any, *, method: str) -> FigmaConsoleResponseError:
    msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
    return FigmaConsoleResponseError(f"{method} failed: {msg}")


def _is_retryable_console_error(exc: Exception) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, OSError, ConnectionError, FigmaConsoleRetryableError)):
        return True
    text = str(exc).lower()
    return any(token in text for token in ("timeout", "timed out", "temporarily unavailable", "connection reset"))


async def _sleep_backoff(attempt: int, *, base_delay: float, max_delay: float) -> None:
    delay = min(base_delay * (2 ** max(0, attempt - 1)), max_delay)
    if delay > 0:
        await asyncio.sleep(delay)


@dataclass
class FigmaConsoleProxy:
    """WebSocket 代理：轉發 client JSON-RPC ↔ Figma plugin。"""

    host: str = "0.0.0.0"
    port: int = 3055
    plugin_timeout_s: float = 60.0

    _plugins: Dict[Any, str] = field(default_factory=dict)
    _plugin_order: list[Any] = field(default_factory=list)
    _pending: Dict[str, asyncio.Future] = field(default_factory=dict)

    async def _call_figma(self, plugin_ws: Any, method: str, params: Optional[Dict[str, Any]]) -> Any:
        normalized = method[7:] if method.startswith("figma/") else method
        req_id = str(uuid.uuid4())
        payload = {"id": req_id, "method": normalized, "params": params or {}}
        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[req_id] = fut
        await plugin_ws.send(json.dumps(payload))
        try:
            return await asyncio.wait_for(fut, timeout=self.plugin_timeout_s)
        finally:
            self._pending.pop(req_id, None)

    async def _on_plugin_raw(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("plugin 非 JSON，略過")
            return
        rid = msg.get("id")
        if rid and rid in self._pending:
            fut = self._pending.pop(rid)
            if msg.get("error"):
                err = msg["error"]
                text = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                if not fut.done():
                    fut.set_exception(RuntimeError(text))
            else:
                if not fut.done():
                    fut.set_result(msg.get("result"))

    async def _handler(self, websocket: Any) -> None:
        try:
            path = websocket.request.path
        except Exception:
            path = "/"
        role = (parse_qs(urlparse(path).query).get("role") or ["plugin"])[0]

        if role == "plugin":
            pid = str(uuid.uuid4())
            self._plugins[websocket] = pid
            self._plugin_order.append(websocket)
            log.info("Figma plugin 已連線 id=%s", pid)
            try:
                async for raw in websocket:
                    await self._on_plugin_raw(_decode_msg(raw))
            finally:
                self._plugins.pop(websocket, None)
                if websocket in self._plugin_order:
                    self._plugin_order.remove(websocket)
                log.info("Figma plugin 已斷線 id=%s", pid)
            return

        log.info("CLI client 已連線")
        try:
            async for raw in websocket:
                try:
                    req = json.loads(_decode_msg(raw))
                except json.JSONDecodeError as e:
                    await websocket.send(json.dumps({"id": None, "error": {"message": str(e)}}))
                    continue
                cid = req.get("id")
                method = req.get("method")
                params = req.get("params")
                if not method:
                    await websocket.send(json.dumps({"id": cid, "error": {"message": "缺少 method"}}))
                    continue
                if not self._plugin_order:
                    await websocket.send(
                        json.dumps({"id": cid, "error": {"message": "尚無 Figma plugin 連線"}})
                    )
                    continue
                plugin_ws = self._plugin_order[-1]
                try:
                    pdict = params if isinstance(params, dict) else {}
                    result = await self._call_figma(plugin_ws, method, pdict)
                    await websocket.send(json.dumps({"id": cid, "result": result}))
                except Exception as e:
                    await websocket.send(json.dumps({"id": cid, "error": {"message": str(e)}}))
        finally:
            log.info("CLI client 已斷線")


def run_server_blocking(host: str = "0.0.0.0", port: int = 3055) -> None:
    """阻塞執行 WebSocket 代理。"""
    proxy = FigmaConsoleProxy(host=host, port=port)

    async def _main() -> None:
        _require_ws_libs()
        log.warning(
            "Figma Console WS 代理 ws://%s:%s （Figma 請連 ?role=plugin；CLI 請連 ?role=client）",
            host if host != "0.0.0.0" else "localhost",
            port,
        )
        async with ws_serve(proxy._handler, host, port):
            await asyncio.Future()

    asyncio.run(_main())


async def request_async(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    host: str = "localhost",
    port: int = 3055,
    timeout: float = 120.0,
    retries: int = 0,
    retry_backoff_s: float = 0.25,
    retry_backoff_max_s: float = 2.0,
    trace_id: Optional[str] = None,
    verbose: bool = False,
) -> Any:
    """client 身分送出一則請求（與 TypeScript FigmaClient 相同載具格式）。"""
    _require_ws_libs()
    uri = f"ws://{host}:{port}/?role=client"
    req_id = 1
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
    attempts = retries + 1
    last_error: Optional[Exception] = None
    request_trace_id = trace_id or str(uuid.uuid4())
    for attempt in range(1, attempts + 1):
        started = time.perf_counter()
        try:
            if verbose:
                log.info(
                    "figma-console request start trace_id=%s method=%s attempt=%s/%s host=%s port=%s",
                    request_trace_id,
                    method,
                    attempt,
                    attempts,
                    host,
                    port,
                )
            async with ws_connect(uri, open_timeout=timeout) as conn:
                await conn.send(json.dumps(payload))
                raw = await asyncio.wait_for(conn.recv(), timeout=timeout)
                data = json.loads(_decode_msg(raw))
                if data.get("error"):
                    raise _normalize_response_error(data["error"], method=method)
                if verbose:
                    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
                    log.info(
                        "figma-console request success trace_id=%s method=%s attempt=%s/%s elapsed_ms=%s",
                        request_trace_id,
                        method,
                        attempt,
                        attempts,
                        elapsed_ms,
                    )
                return data.get("result")
        except Exception as exc:
            if isinstance(exc, FigmaConsoleResponseError):
                if verbose:
                    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
                    log.warning(
                        "figma-console request response-error trace_id=%s method=%s attempt=%s/%s elapsed_ms=%s error=%s",
                        request_trace_id,
                        method,
                        attempt,
                        attempts,
                        elapsed_ms,
                        exc,
                    )
                raise
            retryable = _is_retryable_console_error(exc)
            last_error = _normalize_retryable_error(exc, method=method, attempt=attempt) if retryable else exc
            if (not retryable) or attempt >= attempts:
                if verbose:
                    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
                    log.warning(
                        "figma-console request failed trace_id=%s method=%s attempt=%s/%s elapsed_ms=%s retryable=%s error=%s",
                        request_trace_id,
                        method,
                        attempt,
                        attempts,
                        elapsed_ms,
                        retryable,
                        last_error,
                    )
                raise last_error
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            log.warning(
                "figma-console request retrying trace_id=%s method=%s attempt=%s/%s next_attempt=%s elapsed_ms=%s reason=%s",
                request_trace_id,
                method,
                attempt,
                attempts,
                attempt + 1,
                elapsed_ms,
                exc,
            )
            await _sleep_backoff(
                attempt,
                base_delay=retry_backoff_s,
                max_delay=retry_backoff_max_s,
            )
    if last_error:
        raise last_error
    raise FigmaConsoleRetryableError(f"{method} failed without a recorded error")


def request_sync(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    host: str = "localhost",
    port: int = 3055,
    timeout: float = 120.0,
    retries: int = 0,
    retry_backoff_s: float = 0.25,
    retry_backoff_max_s: float = 2.0,
    trace_id: Optional[str] = None,
    verbose: bool = False,
) -> Any:
    return asyncio.run(
        request_async(
            method,
            params,
            host=host,
            port=port,
            timeout=timeout,
            retries=retries,
            retry_backoff_s=retry_backoff_s,
            retry_backoff_max_s=retry_backoff_max_s,
            trace_id=trace_id,
            verbose=verbose,
        )
    )
