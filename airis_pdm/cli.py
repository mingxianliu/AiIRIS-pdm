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
import time
import re
import threading
import requests
from pathlib import Path
from watchdog.observers import Observer
from airis_pdm import __version__
from watchdog.events import FileSystemEventHandler

# 確保可載入同套件
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from .naming_engine import preview_naming_tree
from .dom_extractor import extract_dom_tree, ExtractionConfig
from .ir_builder import build_ir_from_extraction, save_ir
from .figma_reader import FigmaAPIClient, FigmaToIR, IRDiffer
from .code_patcher import CodePatcher
from .config import load_config
from .generator import generate_project
from .token_export import export_tokens
from .design_assets import _count_nodes


async def process_url_to_ir(url: str, args, config: dict, viewport_override=None):
    """Helper: Extract DOM and build IR for a single URL.

    Returns:
        (ir_doc, extraction_result) tuple, or (None, None) on failure.
    """
    viewport = config.get("viewport", {})
    if viewport_override:
        viewport = viewport_override
    elif args.viewport:
        w, h = args.viewport.split("x")
        viewport = {"width": int(w), "height": int(h)}

    extraction_config = ExtractionConfig(
        viewport_width=viewport.get("width", 1440),
        viewport_height=viewport.get("height", 900),
        framework=config.get("source", {}).get("framework", "html"),
        root_selector=args.selector or args.root or "#app, #root, #__nuxt, body",
    )

    try:
        result = await extract_dom_tree(url, extraction_config)
    except Exception as e:
        print(f"   ❌ Extraction failed for {url}: {e}")
        return None, None

    if not result["tree"]:
        return None, None

    ir_doc = build_ir_from_extraction(result, config)
    return ir_doc, result


async def perform_push(url: str, args, config: dict):
    """Core push logic, extracted for reuse by push and watch commands."""
    print(f"🚀 Pushing to Figma from: {url}")

    ir_doc, result = await process_url_to_ir(url, args, config)
    if not ir_doc:
        print("   ❌ Failed to generate IR.")
        return

    node_count = _count_nodes(ir_doc["tree"])
    print(f"   ✅ Named {node_count} nodes")

    output_dir = config.get("export", {}).get("snapshotDir", ".figma-sync")
    os.makedirs(output_dir, exist_ok=True)

    print("   [3/4] Saving IR snapshot...")
    ir_path, mapping_path = save_ir(ir_doc, output_dir)
    print(f"   ✅ Saved to {ir_path}")

    # 寫出截圖
    screenshot_bytes = result.get("screenshot")
    if screenshot_bytes:
        screenshot_path = os.path.join(output_dir, "reference-screenshot.png")
        with open(screenshot_path, "wb") as f:
            f.write(screenshot_bytes)
        print(f"   📸 Screenshot saved to {screenshot_path}")


async def cmd_push_stories(args, config: dict):
    """Fetch stories from Storybook and batch export."""
    sb_url = args.url.rstrip("/")
    print(f"📚 Fetching stories from: {sb_url}")
    
    # 1. Try to fetch stories.json
    try:
        resp = requests.get(f"{sb_url}/stories.json", timeout=5)
        if resp.status_code != 200:
            print(f"   ⚠️ Could not fetch /stories.json (Status {resp.status_code}). Is this Storybook 6.4+?")
            return
        stories_data = resp.json().get("stories", {})
    except Exception as e:
        print(f"   ❌ Error fetching stories list: {e}")
        return

    # 2. Filter stories
    stories_to_sync = []
    filter_re = re.compile(args.filter) if args.filter else None

    for story_id, story in stories_data.items():
        if filter_re and not filter_re.search(story.get("name", "")):
            continue
        stories_to_sync.append(story)
    
    print(f"   ✅ Found {len(stories_to_sync)} stories to sync.")
    
    # 3. Process each story
    # 其他參數
    combined_children = []
    comp_width = 800
    comp_height = 600
    # Storybook iframe 的根元素通常是 #root，用 local 變數避免污染 args
    sb_selector = "#root, #docs-root, body"

    for i, story in enumerate(stories_to_sync):
        s_id = story["id"]
        s_name = story.get("name", s_id)
        s_kind = story.get("kind", "Stories")
        iframe_url = f"{sb_url}/iframe.html?id={s_id}&viewMode=story"
        
        print(f"   [{i+1}/{len(stories_to_sync)}] Processing {s_kind}/{s_name}...")
        
        # Reuse process_url_to_ir logic (inline here for safety)
        # We need a fresh config for each? No, config is static.
        
        # We need to construct a "Frame" for this story
        # Layout them horizontally
        spacing = 100
        x_pos = i * (comp_width + spacing)
        
        extraction_config = ExtractionConfig(
            viewport_width=comp_width,
            viewport_height=comp_height,
            framework=config.get("source", {}).get("framework", "html"),
            root_selector=sb_selector,
        )
        
        try:
            result = await extract_dom_tree(iframe_url, extraction_config)
            raw_tree = result["tree"]
            if raw_tree:
                # Build IR for this story
                # We need to wrap it in a Frame named after the story
                ir_doc = build_ir_from_extraction(result, config)
                story_root = ir_doc["tree"]
                
                # Override name
                story_root["figmaName"] = f"{s_kind}/{s_name}"
                story_root["layout"]["x"] = x_pos
                story_root["layout"]["y"] = 0
                
                combined_children.append(story_root)
        except Exception as e:
            print(f"      ⚠️ Failed: {e}")

    # 4. Save combined payload
    if not combined_children:
        print("   ❌ No stories extracted.")
        return

    output_dir = config.get("export", {}).get("snapshotDir", ".figma-sync")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a synthetic root
    combined_root = {
        "figmaName": "Storybook Sync",
        "figmaType": "FRAME", # Or just a container
        "htmlTag": "div",
        "children": combined_children,
        "layout": {"x":0, "y":0, "width": 1000, "height": 1000}
    }
    
    print("   [4/4] Saving Storybook snapshot...")
    # Reuse save logic manually
    plugin_path = os.path.join(output_dir, "plugin-payload.json")
    with open(plugin_path, 'w', encoding='utf-8') as f:
        json.dump(combined_root, f, indent=2, ensure_ascii=False)
        
    print(f"   ✅ Saved {len(combined_children)} stories to {plugin_path}")
    print("   Load this in Figma Plugin to see all components!")


async def cmd_push(args, config: dict):
    """Push: 擷取 DOM → 建 IR → 寫出 payload 給 Figma Plugin."""
    await perform_push(args.url, args, config)


_WATCHED_EXTENSIONS = (".vue", ".js", ".ts", ".jsx", ".tsx", ".css", ".scss", ".html")


class ChangeHandler(FileSystemEventHandler):
    """檔案變更事件處理器，帶 debounce 防抖。"""

    def __init__(self, callback, loop: asyncio.AbstractEventLoop, debounce: float = 1.0):
        self.callback = callback
        self.loop = loop
        self.last_trigger = 0.0
        self.debounce_seconds = debounce

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(_WATCHED_EXTENSIONS):
            return
        current_time = time.time()
        if current_time - self.last_trigger < self.debounce_seconds:
            return
        self.last_trigger = current_time
        print(f"\n🔄 File changed: {event.src_path}")
        # 透過 threadsafe 把 coroutine 丟進 loop（loop 在獨立執行緒中 run_forever）
        asyncio.run_coroutine_threadsafe(self.callback(), self.loop)


def cmd_watch(args, config: dict):
    """Watch: 監聽檔案變更並自動執行 push."""
    url = args.url
    src_dir = config.get("source", {}).get("srcRoot", ".") or "."
    print(f"👀 Watching for changes in '{src_dir}'...")
    print(f"   Target URL: {url}")
    print("   Press Ctrl+C to stop.")

    # 在獨立執行緒中運行 event loop，避免主執行緒與 coroutine_threadsafe 競爭
    loop = asyncio.new_event_loop()

    async def push_task():
        await perform_push(url, args, config)

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    loop_thread = threading.Thread(target=run_loop, daemon=True)
    loop_thread.start()

    # 初始執行一次 push（等待完成）
    future = asyncio.run_coroutine_threadsafe(push_task(), loop)
    try:
        future.result(timeout=120)  # 最多等 2 分鐘
    except Exception as e:
        print(f"   ⚠️  Initial push failed: {e}")

    event_handler = ChangeHandler(push_task, loop)
    observer = Observer()
    observer.schedule(event_handler, path=src_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping watch...")
        observer.stop()
    finally:
        observer.join()
        loop.call_soon_threadsafe(loop.stop)


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
                # P3 #15：與 push/watch 一致，支援 --selector
                root_selector=getattr(args, "selector", None) or "#app, #root, #__nuxt, body",
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
        print("❌ 請設定 FIGMA_TOKEN 環境變數，或在 figma-sync.config.json 的 figma.personalAccessToken 設定。")
        print("   取得方式：Figma → Settings → Personal access tokens → 新增")
        return
    if not file_key:
        print("❌ 請使用 --file-key 或在 config 的 figma.fileKey 設定 Figma 檔案 key。")
        return

    print(f"📥 Pulling from Figma: {file_key}")

    output_dir = config.get("export", {}).get("snapshotDir", ".figma-sync")
    snapshot_path = os.path.join(output_dir, "figma-import-payload.json")
    if not os.path.exists(snapshot_path):
        print("❌ 找不到 push 快照，請先執行 'figma-sync push <url>'。")
        return

    with open(snapshot_path, "r", encoding="utf-8") as f:
        before_ir = json.load(f)
    print("   ✅ Loaded snapshot")

    # Figma API — 友善錯誤訊息
    client = FigmaAPIClient(token)
    try:
        figma_data = client.get_file(file_key)
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status == 403:
            print("❌ Figma API 403：Token 無效或已過期，請重新產生 FIGMA_TOKEN。")
        elif status == 404:
            print(f"❌ Figma API 404：找不到檔案 '{file_key}'，請確認 file key 是否正確。")
        else:
            print(f"❌ Figma API 錯誤：{e}")
        return

    document = figma_data.get("document", {})
    pages = document.get("children", [])
    if not pages:
        print("❌ 此 Figma 檔案沒有任何頁面。")
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

    # Layout Integrity 警告
    layout_warnings = []
    for node_name, diffs in changes.items():
        if "layout.integrity" in diffs:
            layout_warnings.append(node_name)

    if layout_warnings:
        print("\n   ⚠️  LAYOUT INTEGRITY WARNING:")
        print("   以下 frame 在 Figma 中失去 Auto Layout，回寫準確度可能降低：")
        for name in layout_warnings:
            print(f"     - {name}")
        print()

    mapping_path = os.path.join(output_dir, "name-mapping.json")
    name_mapping = {}
    if os.path.exists(mapping_path):
        with open(mapping_path, "r", encoding="utf-8") as f:
            name_mapping = json.load(f)

    src_root = config.get("source", {}).get("srcRoot", "")
    patcher = CodePatcher(
        name_mapping=name_mapping,
        style_strategy=config.get("source", {}).get("styleStrategy", "tailwind"),
        src_root=src_root,
        dry_run=not args.apply,
    )
    print()
    print(patcher.generate_patch_report(changes))

    if args.apply:
        if not src_root:
            print("⚠️  source.srcRoot 未設定，將嘗試使用 name_mapping 中的路徑。")
        print("\n🔧 Applying changes to source files...")
        summary = patcher.apply_changes(changes)
        if not summary:
            print("   ℹ️  沒有可套用的變更（可能是 selector 找不到對應檔案）。")
        for filepath, applied in summary.items():
            print(f"   📄 {filepath}:")
            for line in applied:
                print(line)
        print("   ✅ Done.")
    else:
        print("\n   💡 使用 --apply 將變更套用到原始碼（需設定 source.srcRoot）。")

    diff_path = os.path.join(output_dir, "last-diff.json")
    with open(diff_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, indent=2, ensure_ascii=False)
    print(f"   📄 Diff saved to {diff_path}")


def cmd_generate(args, config: dict):
    """Generate: 從 Figma 產生新前端（不需要 push 快照）."""
    figma_cfg = config.get("figma", {})
    token = figma_cfg.get("personalAccessToken") or os.environ.get("FIGMA_TOKEN")
    file_key = figma_cfg.get("fileKey") or args.file_key

    if not token:
        print("❌ 請設定 FIGMA_TOKEN 環境變數，或在 figma-sync.config.json 的 figma.personalAccessToken 設定。")
        return
    if not file_key:
        print("❌ 請使用 --file-key 或在 config 的 figma.fileKey 設定 Figma 檔案 key。")
        return

    target = (args.target or "html").lower()
    output_dir = args.output or "./generated"

    try:
        generate_project(
            figma_token=token,
            file_key=file_key,
            target=target,
            output_dir=output_dir,
            page_name=args.page,
            page_index=args.page_index,
            all_pages=args.all_pages,
            include_utility_css=args.with_utility_css,
        )
    except Exception as e:
        print(f"❌ Generate failed: {e}")
        return

    print(f"✅ Generated {target} project to {output_dir}")


def cmd_export_tokens(args):
    """從 IR 產出 design tokens（tokens.json 或 CSS 變數）。"""
    try:
        written = export_tokens(
            ir_path_or_dir=args.from_dir,
            output_path=args.output,
            format=args.format,
            css_prefix=args.css_prefix,
        )
        print(f"✅ Tokens 已寫入: {written}")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   請先執行 'figma-sync push <url>' 產生 IR。")
    except Exception as e:
        print(f"❌ export-tokens 失敗: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="AiIRIS-pdm: Code ↔ Figma Bidirectional Sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", "-c", default="figma-sync.config.json", help="Config path")
    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    push_p = sub.add_parser("push", help="Code → Figma",
        epilog="Examples:\n  figma-sync push http://localhost:5173\n  figma-sync push http://localhost:5173 --viewport 375x812\n  figma-sync push http://localhost:5173 --selector '#login-form'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    push_p.add_argument("url", help="App URL (e.g. http://localhost:5173)")
    push_p.add_argument("--viewport", help="WxH e.g. 375x812")
    push_p.add_argument("--root", help="Root selector (deprecated, use --selector)")
    push_p.add_argument("--selector", help="Partial sync: CSS selector to capture (e.g. '#login-form')")
    push_p.add_argument("--erslice", action="store_true", help="Write ErSlice manifest & completeness")
    push_p.add_argument("--erslice-module", default="default", help="Module name for manifest")
    push_p.add_argument("--erslice-page", default="page", help="Page slug for manifest")

    watch_p = sub.add_parser("watch", help="Watch for file changes and auto-push",
        epilog="Examples:\n  figma-sync watch http://localhost:5173\n  figma-sync watch http://localhost:5173 --viewport 375x812",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    watch_p.add_argument("url", help="App URL (e.g. http://localhost:5173)")
    watch_p.add_argument("--viewport", help="WxH e.g. 375x812")
    watch_p.add_argument("--root", help="Root selector (deprecated, use --selector)")
    watch_p.add_argument("--selector", help="Partial sync: CSS selector to capture (e.g. '#login-form')")
    watch_p.add_argument("--erslice", action="store_true", help="Write ErSlice manifest & completeness")
    watch_p.add_argument("--erslice-module", default="default", help="Module name for manifest")
    watch_p.add_argument("--erslice-page", default="page", help="Page slug for manifest")

    stories_p = sub.add_parser("push-stories", help="Batch sync from Storybook",
        epilog="Examples:\n  figma-sync push-stories http://localhost:6006\n  figma-sync push-stories http://localhost:6006 --filter 'Button'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    stories_p.add_argument("url", help="Storybook URL (e.g. http://localhost:6006)")
    stories_p.add_argument("--filter", help="Filter stories by name (regex)")

    preview_p = sub.add_parser("preview", help="Preview naming tree",
        epilog="Examples:\n  figma-sync preview http://localhost:5173\n  figma-sync preview http://localhost:5173 --selector '#sidebar'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    preview_p.add_argument("url", help="App URL")
    preview_p.add_argument("--selector", help="CSS selector to preview (e.g. '#sidebar')")

    pull_p = sub.add_parser("pull", help="Figma → Code",
        epilog="Examples:\n  figma-sync pull --file-key ABC123\n  figma-sync pull --file-key ABC123 --apply",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    pull_p.add_argument("--file-key", help="Figma file key")
    pull_p.add_argument("--apply", action="store_true", help="Apply patches to source (needs source.srcRoot in config)")

    gen_p = sub.add_parser("generate", help="Figma → New Frontend",
        epilog="Examples:\n  figma-sync generate --file-key ABC123 --target react --output ./out\n  figma-sync generate --file-key ABC123 --target flutter --page 'Home'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    gen_p.add_argument("--file-key", help="Figma file key")
    gen_p.add_argument("--target", choices=["react", "vue", "html", "flutter"], help="Output target")
    gen_p.add_argument("--output", help="Output directory")
    gen_p.add_argument("--page", help="Page name to export")
    gen_p.add_argument("--page-index", type=int, help="Page index to export")
    gen_p.add_argument("--all-pages", action="store_true", help="Export all pages")
    gen_p.add_argument("--with-utility-css", action="store_true", help="Emit styles/utility.css and app.css import")

    export_p = sub.add_parser("export-tokens", help="從 IR 產出 design tokens (tokens.json 或 CSS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  figma-sync export-tokens\n  figma-sync export-tokens --from-dir .figma-sync --output tokens.json --format css")
    export_p.add_argument("--from-dir", default=".figma-sync", help="IR 目錄（內含 figma-import-payload.json）")
    export_p.add_argument("--output", "-o", default="tokens.json", help="輸出檔路徑")
    export_p.add_argument("--format", choices=["json", "css"], default="json", help="輸出格式")
    export_p.add_argument("--css-prefix", default="--token", help="CSS 變數前綴（僅 format=css 時使用）")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "push":
        asyncio.run(cmd_push(args, config))
    elif args.command == "watch":
        cmd_watch(args, config)
    elif args.command == "push-stories":
        asyncio.run(cmd_push_stories(args, config))
    elif args.command == "preview":
        cmd_preview(args, config)
    elif args.command == "pull":
        cmd_pull(args, config)
    elif args.command == "generate":
        cmd_generate(args, config)
    elif args.command == "export-tokens":
        cmd_export_tokens(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
