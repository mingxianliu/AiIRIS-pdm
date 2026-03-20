import json
import logging
from pathlib import Path
from types import SimpleNamespace

from airis_pdm.figmai import run_chain_pipeline, run_flow_from_file_json, run_flow_via_console
from airis_pdm.figmai.renderers import render_pixel_react_component, render_pixel_vue_sfc
from airis_pdm.figmai.spec_to_design_ops import spec_to_design_ops
from airis_pdm.cli import (
    EXIT_FIGMA_CONSOLE_RESPONSE,
    EXIT_FIGMA_CONSOLE_RETRYABLE,
    EXIT_OK,
    cmd_figma_console,
    cmd_figma_mai,
)
from airis_pdm.figma_console_ws import FigmaConsoleResponseError, FigmaConsoleRetryableError


def _sample_figma_file() -> dict:
    return {
        "document": {
            "type": "DOCUMENT",
            "children": [
                {
                    "type": "CANVAS",
                    "name": "Main",
                    "children": [
                        {
                            "id": "1:1",
                            "type": "FRAME",
                            "name": "[Page] Login",
                            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                            "children": [
                                {
                                    "id": "1:2",
                                    "type": "TEXT",
                                    "name": "Title",
                                    "characters": "Hello",
                                    "style": {"fontSize": 24, "fontFamily": "Inter", "fontWeight": 700},
                                    "absoluteBoundingBox": {"x": 20, "y": 20, "width": 100, "height": 28},
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    }


def test_spec_to_design_ops_minimal():
    spec = {"name": "Auth", "sections": [{"type": "card", "name": "LoginCard"}]}
    node = spec_to_design_ops(spec)
    assert node["type"] == "component"
    assert node["children"][0]["name"] == "LoginCard"


def test_pixel_renderers():
    root = _sample_figma_file()["document"]["children"][0]["children"][0]
    react = render_pixel_react_component(root)
    vue = render_pixel_vue_sfc(root)
    assert "pixel-root" in react["tsx"]
    assert "pixel-root" in vue


def test_flow_semantic(tmp_path: Path):
    payload = _sample_figma_file()
    src = tmp_path / "figma.json"
    src.write_text(json.dumps(payload), encoding="utf-8")
    manifest = run_flow_from_file_json(
        figma_file_json_path=str(src),
        output_dir=str(tmp_path / "out"),
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
    )
    assert manifest["count"] == 1
    assert manifest["counts"]["generated"] == 1
    assert len(manifest["pages"]) == 1
    assert manifest["pages"][0]["displayName"] == "Login"
    assert manifest["pages"][0]["routePath"] == "/login"
    assert (tmp_path / "out" / "flow" / "manifest.json").is_file()


def test_chain_local(tmp_path: Path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "name": "Auth",
                "sections": [
                    {
                        "type": "form",
                        "name": "Login",
                        "children": [
                            {"type": "text", "name": "Title", "props": {"text": "Login Now", "fontSize": 20}}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "chain"), target="html")
    assert result["success"] is True
    assert any(s["name"] == "codegen" and s["status"] == "completed" for s in result["stages"])
    html = (tmp_path / "chain" / "index.html").read_text(encoding="utf-8")
    assert "Login Now" in html


def test_flow_live_console(monkeypatch, tmp_path: Path):
    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        if method == "searchNodes":
            return [{"id": "1:1", "name": "[Page] Login", "type": "FRAME"}]
        if method == "getNode":
            return {
                "id": "1:1",
                "name": "[Page] Login",
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                "children": [],
            }
        if method == "notify":
            return True
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_request_sync)
    manifest = run_flow_via_console(
        output_dir=str(tmp_path / "live"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
        notify=True,
    )
    assert manifest["counts"]["generated"] == 1
    assert manifest["count"] == 1
    assert len(manifest["generated"]) == 1
    assert (tmp_path / "live" / "flow" / "manifest.json").is_file()
    assert (tmp_path / "live" / "flow" / "vue" / "router.ts").is_file()


def test_cli_flow_live_count_message(monkeypatch, capsys):
    args = SimpleNamespace(
        fm_cmd="flow",
        live=True,
        output="./generated",
        host="localhost",
        port=3055,
        pattern="[Page]",
        include="",
        exclude="",
        framework="vue",
        fidelity="semantic",
        depth=8,
        notify=False,
        json_file="",
        rpc_timeout=12.0,
        rpc_retries=2,
        rpc_backoff=0.4,
        rpc_backoff_max=1.5,
        trace_id="trace-flow",
        verbose=True,
    )

    seen = {}

    def fake_flow(**kwargs):
        seen.update(kwargs)
        return {"counts": {"generated": 3}, "pages": []}

    monkeypatch.setattr("airis_pdm.figmai.run_flow_via_console", fake_flow)
    assert cmd_figma_mai(args) == EXIT_OK
    out = capsys.readouterr().out
    assert "共 3 頁" in out
    assert seen["rpc_timeout"] == 12.0
    assert seen["rpc_retries"] == 2
    assert seen["rpc_retry_backoff_s"] == 0.4
    assert seen["rpc_retry_backoff_max_s"] == 1.5
    assert seen["trace_id"] == "trace-flow"
    assert seen["verbose"] is True


def test_cli_chain_retryable_console_error_returns_exit_code(monkeypatch, capsys):
    args = SimpleNamespace(
        fm_cmd="chain",
        spec_file="spec.json",
        output="./generated",
        target="vue",
        host="localhost",
        port=3055,
        depth=8,
        sync=False,
        figma_node_id=None,
        with_utility_css=False,
        state_dir=None,
        missing_node_strategy="orphan",
        rpc_timeout=10.0,
        rpc_retries=1,
        rpc_backoff=0.25,
        rpc_backoff_max=1.0,
        trace_id="trace-chain",
        verbose=True,
    )

    def fake_chain(**kwargs):
        raise FigmaConsoleRetryableError("searchNodes failed on attempt 2: timeout")

    monkeypatch.setattr("airis_pdm.figmai.run_chain_remote", fake_chain)
    code = cmd_figma_mai(args)
    out = capsys.readouterr().out
    assert code == EXIT_FIGMA_CONSOLE_RETRYABLE
    assert "chain 失敗" in out


def test_cli_flow_response_error_returns_exit_code(monkeypatch, capsys):
    args = SimpleNamespace(
        fm_cmd="flow",
        live=True,
        output="./generated",
        host="localhost",
        port=3055,
        pattern="[Page]",
        include="",
        exclude="",
        framework="vue",
        fidelity="semantic",
        depth=8,
        notify=False,
        json_file="",
        rpc_timeout=10.0,
        rpc_retries=1,
        rpc_backoff=0.25,
        rpc_backoff_max=1.0,
        trace_id="trace-flow-err",
        verbose=True,
    )

    def fake_flow(**kwargs):
        raise FigmaConsoleResponseError("getNode failed: method not supported")

    monkeypatch.setattr("airis_pdm.figmai.run_flow_via_console", fake_flow)
    code = cmd_figma_mai(args)
    out = capsys.readouterr().out
    assert code == EXIT_FIGMA_CONSOLE_RESPONSE
    assert "flow 失敗" in out


def test_cli_figma_console_request_uses_retry_args_and_returns_ok(monkeypatch, capsys):
    args = SimpleNamespace(
        fc_cmd="request",
        fc_method="getNode",
        fc_params='{"nodeId":"1:1"}',
        fc_host="localhost",
        fc_port=3055,
        rpc_timeout=9.0,
        rpc_retries=3,
        rpc_backoff=0.3,
        rpc_backoff_max=2.5,
        trace_id="trace-console",
        verbose=True,
    )
    seen = {}

    def fake_request_sync(method, params, **kwargs):
        seen["method"] = method
        seen["params"] = params
        seen.update(kwargs)
        return {"id": "1:1"}

    monkeypatch.setattr("airis_pdm.figma_console_ws.request_sync", fake_request_sync)
    assert cmd_figma_console(args) == EXIT_OK
    out = capsys.readouterr().out
    assert '"id": "1:1"' in out
    assert seen["timeout"] == 9.0
    assert seen["retries"] == 3
    assert seen["retry_backoff_s"] == 0.3
    assert seen["retry_backoff_max_s"] == 2.5
    assert seen["trace_id"] == "trace-console"
    assert seen["verbose"] is True


def test_flow_live_verbose_logs_summary(monkeypatch, tmp_path: Path, caplog):
    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        if method == "searchNodes":
            return [{"id": "1:1", "name": "[Page] Login", "type": "FRAME"}]
        if method == "getNode":
            return {
                "id": "1:1",
                "name": "[Page] Login",
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                "children": [],
            }
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_request_sync)
    with caplog.at_level(logging.INFO):
        manifest = run_flow_via_console(
            output_dir=str(tmp_path / "live"),
            framework="vue",
            fidelity="semantic",
            trace_id="trace-live",
            verbose=True,
        )

    assert manifest["count"] == 1
    assert "figmai flow live completed trace_id=trace-live" in caplog.text
