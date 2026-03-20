#!/usr/bin/env python3
"""
diff_against_baseline.py — 標準化 baseline 對拍報告

用途：
  python scripts/diff_against_baseline.py [--baseline-dir tests/golden] [--output-dir /tmp/parity_run]

做法：
  1. 以 chain-local 跑所有 golden spec，產出到 output-dir
  2. 以 flow offline 跑 Figma file JSON fixture，產出 manifest
  3. 比對 golden 與產出，列出差異

退出碼：
  0 = 全部一致
  1 = 有差異
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

# 加入專案 root 到 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from airis_pdm.figmai import run_chain_pipeline, run_flow_from_file_json


def _file_tree(root: Path) -> list[str]:
    out = []
    for dirpath, _dirs, fnames in os.walk(str(root)):
        for fn in fnames:
            out.append(os.path.relpath(os.path.join(dirpath, fn), str(root)))
    return sorted(out)


def _diff_text(label: str, expected: str, got: str) -> list[str]:
    if expected == got:
        return []
    diffs = []
    exp_lines = expected.splitlines(keepends=True)
    got_lines = got.splitlines(keepends=True)
    max_lines = max(len(exp_lines), len(got_lines))
    for i in range(max_lines):
        el = exp_lines[i] if i < len(exp_lines) else "<missing>\n"
        gl = got_lines[i] if i < len(got_lines) else "<missing>\n"
        if el != gl:
            diffs.append(f"  line {i+1}:")
            diffs.append(f"    exp: {el.rstrip()}")
            diffs.append(f"    got: {gl.rstrip()}")
    return [f"[DIFF] {label}"] + diffs


def run_chain_parity(baseline_dir: Path, output_dir: Path) -> list[str]:
    """對每個 golden spec 跑 chain-local html，回傳差異報告。"""
    issues: list[str] = []
    specs = list(baseline_dir.glob("spec_*.json"))
    if not specs:
        issues.append("[WARN] No spec_*.json found in baseline-dir")
        return issues

    for spec_file in sorted(specs):
        name = spec_file.stem
        spec_out = output_dir / "chain" / name
        try:
            result = run_chain_pipeline(
                spec_path=str(spec_file),
                output_dir=str(spec_out),
                target="html",
            )
            if not result["success"]:
                issues.append(f"[FAIL] chain-local {name}: pipeline failed")
                continue

            # 檔案樹比對
            tree = _file_tree(spec_out)
            expected_tree = ["index.html", "styles/app.css"]
            if tree != expected_tree:
                issues.append(f"[DIFF] {name} file tree: expected {expected_tree}, got {tree}")

            # 兩次跑的穩定性
            spec_out2 = output_dir / "chain" / f"{name}_run2"
            run_chain_pipeline(spec_path=str(spec_file), output_dir=str(spec_out2), target="html")
            for rel in tree:
                c1 = (spec_out / rel).read_bytes()
                c2 = (spec_out2 / rel).read_bytes()
                if c1 != c2:
                    issues.append(f"[DIFF] {name}/{rel}: not idempotent (two runs differ)")

        except Exception as e:
            issues.append(f"[ERROR] chain-local {name}: {e}")

    return issues


def run_flow_manifest_parity(baseline_dir: Path, output_dir: Path) -> list[str]:
    """比對 flow_disk golden manifest。"""
    issues: list[str] = []
    flow_disk = baseline_dir / "flow_disk"
    if not flow_disk.exists():
        return issues

    # 已有的 offline golden
    offline_golden = flow_disk / "manifest_offline_two_pages.json"
    if offline_golden.exists():
        figma_file = {
            "document": {
                "children": [
                    {
                        "name": "Canvas",
                        "type": "CANVAS",
                        "children": [
                            {
                                "id": "1:1",
                                "name": "[Page] Login",
                                "type": "FRAME",
                                "visible": True,
                                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                                "children": [],
                            },
                            {
                                "id": "1:2",
                                "name": "[Page] Register",
                                "type": "FRAME",
                                "visible": True,
                                "absoluteBoundingBox": {"x": 400, "y": 0, "width": 320, "height": 640},
                                "children": [],
                            },
                        ],
                    }
                ]
            }
        }
        fpath = output_dir / "figma_offline.json"
        fpath.write_text(json.dumps(figma_file), encoding="utf-8")
        try:
            run_flow_from_file_json(
                figma_file_json_path=str(fpath),
                output_dir=str(output_dir / "flow_offline"),
                pattern="[Page]",
                framework="both",
                fidelity="semantic",
            )
            got = (output_dir / "flow_offline" / "flow" / "manifest.json").read_text(encoding="utf-8")
            exp = offline_golden.read_text(encoding="utf-8")
            issues.extend(_diff_text("flow_offline manifest", exp, got))
        except Exception as e:
            issues.append(f"[ERROR] flow offline: {e}")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Baseline parity diff report")
    parser.add_argument("--baseline-dir", default="tests/golden", help="Golden baseline directory")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: temp)")
    args = parser.parse_args()

    baseline = Path(args.baseline_dir).resolve()
    if args.output_dir:
        output = Path(args.output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
    else:
        output = Path(tempfile.mkdtemp(prefix="parity_"))

    print(f"Baseline: {baseline}")
    print(f"Output:   {output}")
    print()

    all_issues: list[str] = []
    all_issues.extend(run_chain_parity(baseline, output))
    all_issues.extend(run_flow_manifest_parity(baseline, output))

    if all_issues:
        print("=" * 60)
        print(f"PARITY ISSUES ({len(all_issues)}):")
        print("=" * 60)
        for issue in all_issues:
            print(issue)
        print()
        print(f"Output preserved at: {output}")
        sys.exit(1)
    else:
        print("=" * 60)
        print("ALL PARITY CHECKS PASSED")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
