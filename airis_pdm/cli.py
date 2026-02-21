#!/usr/bin/env python3
"""
AiIRIS-pdm CLI — Code ↔ Figma 雙向同步

  python -m airis_pdm.cli push <url>       # Code → Figma
  python -m airis_pdm.cli pull --file-key KEY [--apply]  # Figma → Code
  python -m airis_pdm.cli preview <url>    # 預覽命名樹
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# 確保可載入同套件
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from .naming_engine import preview_naming_tree
from .dom_extractor import extract_dom_tree, ExtractionConfig
from .ir_builder import build_ir_from_extraction, save_ir
from .figma_reader import FigmaAPIClient, FigmaToIR, IRDiffer
from .code_patcher import CodePatcher
from .config import load_config


def _count_nodes(tree: dict) -> int:
    n = 1
    for child in tree.get("children", []):
        n += _count_nodes(child)
    return n


async def cmd_push(args, config: dict):
    """Push: 擷取 DOM → 建 IR → 寫出 payload 給 Figma Plugin."""
    url = args.url
    print(f"🚀 Pushing to Figma from: {url}")

    viewport = config.get("viewport", {})
    if args.viewport:
        w, h = args.viewport.split("x")
        viewport = {"width": int(w), "height": int(h)}

    extraction_config = ExtractionConfig(
        viewport_width=viewport.get("width", 1440),
        viewport_height=viewport.get("height", 900),
        framework=config.get("source", {}).get("framework", "html"),
        root_selector=args.selector or args.root or "#app, #root, #__nuxt, body",
    )

    print("   [1/4] Extracting DOM tree...")
    result = await extract_dom_tree(url, extraction_config)
    raw_tree = result["tree"]
    if not raw_tree:
        print("   ❌ Failed to extract DOM tree.")
        return
    print(f"   ✅ DOM extracted ({viewport.get('width', 1440)}x{viewport.get('height', 900)})")

    print("   [2/4] Applying naming rules...")
    ir_doc = build_ir_from_extraction(result, config)
    node_count = _count_nodes(ir_doc["tree"])
    print(f"   ✅ Named {node_count} nodes")

    output_dir = config.get("export", {}).get("snapshotDir", ".figma-sync")
    print("   [3/4] Saving IR snapshot...")
    ir_path, mapping_path = save_ir(ir_doc, output_dir)
    print(f"   ✅ Saved to {ir_path}")

    print("   [4/4] Saving reference screenshot...")
    screenshot_path = os.path.join(output_dir, "reference-screenshot.png")
    with open(screenshot_path, "wb") as f:
        f.write(result["screenshot"])
    print(f"   ✅ Screenshot saved to {screenshot_path}")

    # 選用：ErSlice 風格 manifest / completeness
    if getattr(args, "erslice", False):
        try:
            from .design_assets import write_erslice_manifest, write_completeness
            write_erslice_manifest(output_dir, args.erslice_module or "default", args.erslice_page or "page", ir_doc, url)
            write_completeness(output_dir, ir_doc, has_screenshot=True)
            print("   ✅ ErSlice manifest & completeness written")
        except Exception as e:
            print(f"   ⚠️ ErSlice export skip: {e}")

    print()
    print("═══════════════════════════════════════════════════════")
    print("  ✅ Ready for Figma import!")
    print("═══════════════════════════════════════════════════════")
    print(f"  Load in Figma plugin: {os.path.join(output_dir, 'plugin-payload.json')}")
    print()


def cmd_preview(args, config: dict):
    """預覽命名樹."""
    url = args.url
    print(f"👁️  Preview naming tree: {url}")

    async def run():
        return await extract_dom_tree(
            url,
            ExtractionConfig(
                viewport_width=config.get("viewport", {}).get("width", 1440),
                viewport_height=config.get("viewport", {}).get("height", 900),
                framework=config.get("source", {}).get("framework", "html"),
            ),
        )

    result = asyncio.run(run())
    if not result["tree"]:
        print("❌ Failed to extract DOM tree.")
        return
    ir_doc = build_ir_from_extraction(result, config)
    print(preview_naming_tree(ir_doc["tree"]))
    print(f"\nTotal nodes: {_count_nodes(ir_doc['tree'])}")


def cmd_pull(args, config: dict):
    """Pull: 從 Figma 讀取 → diff → 報告或 --apply 回寫."""
    figma_cfg = config.get("figma", {})
    token = figma_cfg.get("personalAccessToken") or os.environ.get("FIGMA_TOKEN")
    file_key = figma_cfg.get("fileKey") or args.file_key

    if not token:
        print("❌ Set FIGMA_TOKEN or figma.personalAccessToken in config.")
        return
    if not file_key:
        print("❌ Use --file-key or figma.fileKey in config.")
        return

    print(f"📥 Pulling from Figma: {file_key}")

    output_dir = config.get("export", {}).get("snapshotDir", ".figma-sync")
    snapshot_path = os.path.join(output_dir, "figma-import-payload.json")
    if not os.path.exists(snapshot_path):
        print("❌ No snapshot. Run 'push' first.")
        return

    with open(snapshot_path, "r", encoding="utf-8") as f:
        before_ir = json.load(f)
    print("   ✅ Loaded snapshot")

    client = FigmaAPIClient(token)
    figma_data = client.get_file(file_key)
    document = figma_data.get("document", {})
    pages = document.get("children", [])
    if not pages:
        print("❌ No pages in file.")
        return

    converter = FigmaToIR()
    after_ir_tree = converter.convert(pages[0])
    print("   ✅ Fetched Figma file")

    differ = IRDiffer()
    changes = differ.diff(before_ir["tree"], after_ir_tree)
    if not changes:
        print("   ✅ No changes.")
        return

    print(f"   📝 {len(changes)} changed nodes")

    mapping_path = os.path.join(output_dir, "name-mapping.json")
    name_mapping = {}
    if os.path.exists(mapping_path):
        with open(mapping_path, "r", encoding="utf-8") as f:
            name_mapping = json.load(f)

    patcher = CodePatcher(
        name_mapping=name_mapping,
        style_strategy=config.get("source", {}).get("styleStrategy", "tailwind"),
    )
    print()
    print(patcher.generate_patch_report(changes))

    if args.apply:
        print("\n🔧 Applying changes...")
        summary = patcher.apply_changes(changes)
        for filepath, applied in summary.items():
            print(f"   📄 {filepath}:")
            for line in applied:
                print(line)
        print("   ✅ Done.")
    else:
        print("\n   Run with --apply to apply to source files.")

    diff_path = os.path.join(output_dir, "last-diff.json")
    with open(diff_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, indent=2, ensure_ascii=False)
    print(f"   📄 Diff saved to {diff_path}")


def main():
    parser = argparse.ArgumentParser(
        description="AiIRIS-pdm: Code ↔ Figma Bidirectional Sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", "-c", default="figma-sync.config.json", help="Config path")
    sub = parser.add_subparsers(dest="command")

    push_p = sub.add_parser("push", help="Code → Figma")
    push_p.add_argument("url", help="App URL (e.g. http://localhost:5173)")
    push_p.add_argument("--viewport", help="WxH e.g. 375x812")
    push_p.add_argument("--root", help="Root selector (deprecated, use --selector)")
    push_p.add_argument("--selector", help="Partial sync: CSS selector to capture (e.g. '#login-form')")
    push_p.add_argument("--erslice", action="store_true", help="Write ErSlice manifest & completeness")
    push_p.add_argument("--erslice-module", default="default", help="Module name for manifest")
    push_p.add_argument("--erslice-page", default="page", help="Page slug for manifest")

    preview_p = sub.add_parser("preview", help="Preview naming tree")
    preview_p.add_argument("url", help="App URL")

    pull_p = sub.add_parser("pull", help="Figma → Code")
    pull_p.add_argument("--file-key", help="Figma file key")
    pull_p.add_argument("--apply", action="store_true", help="Apply patches to source")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "push":
        asyncio.run(cmd_push(args, config))
    elif args.command == "preview":
        cmd_preview(args, config)
    elif args.command == "pull":
        cmd_pull(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
