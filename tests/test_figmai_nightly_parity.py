import json
from pathlib import Path

from airis_pdm.figmai import run_chain_pipeline, run_flow_via_console
from airis_pdm.figmai.snapshot_anonymizer import anonymize_snapshot


def _snapshot() -> dict:
    p = Path(__file__).parent / "golden" / "nightly" / "real_project_snapshot_anonymized.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_snapshot_anonymizer_stable():
    src = {
        "document": {
            "name": "Internal Product",
            "children": [
                {"name": "[Page] Login", "type": "FRAME"},
                {"name": "Internal Product", "type": "TEXT"},
            ],
        }
    }
    out = anonymize_snapshot(src)
    name1 = out["document"]["name"]
    name2 = out["document"]["children"][1]["name"]
    assert name1 == name2
    assert out["document"]["children"][0]["name"].startswith("[Page] ")


def test_nightly_parity_snapshot(monkeypatch, tmp_path: Path):
    snap = _snapshot()
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(snap["spec"]), encoding="utf-8")

    chain = run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "chain"), target="html")
    assert chain["success"] is True
    html = (tmp_path / "chain" / "index.html").read_text(encoding="utf-8")
    assert snap["expected"]["chain_contains_text"] in html

    search_nodes = snap["flow_live"]["search_nodes"]
    nodes_by_id = snap["flow_live"]["nodes_by_id"]

    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        if method == "searchNodes":
            return search_nodes
        if method == "getNode":
            return nodes_by_id[params["nodeId"]]
        if method == "notify":
            return True
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_request_sync)
    flow = run_flow_via_console(
        output_dir=str(tmp_path / "flow"),
        pattern=snap["flow_live"]["pattern"],
        framework="vue",
        fidelity="semantic",
    )
    assert flow["counts"]["generated"] == snap["expected"]["flow_generated_count"]
    assert [p["slug"] for p in flow["pages"]] == snap["expected"]["flow_slugs"]
