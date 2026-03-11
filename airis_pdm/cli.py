#!/usr/bin/env python3
"""
AiIRIS-pdm CLI — Spec → Pencil AI → Fine-tune → React/Vue Code

  pdm push <url>                          # Code → IR snapshot
  pdm watch <url>                         # Watch + auto push
  pdm codegen <ir-json> --target vue      # IR → React/Vue/HTML/Flutter
  pdm preview <url>                       # 預覽命名樹
  pdm export-tokens                       # IR → design tokens
"""

import argparse
import asyncio
import json
import os
import sys
import time
import re
import threading
from pathlib import Path
from watchdog.observers import Observer
from airis_pdm import __version__
from watchdog.events import FileSystemEventHandler

# 確保可載入同套件
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from .naming_engine import preview_naming_tree
from .dom_extractor import extract_dom_tree, ExtractionConfig
from .ir_builder import build_ir_from_extraction, save_ir
from .code_patcher import CodePatcher
from .config import load_config
from .generator import generate_from_ir
from .pencil_reader import PencilToIR
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
    import requests  # lazy import — legacy dependency

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


def cmd_codegen(args, config: dict):
    """Codegen: 從 IR JSON 或 .pen 節點資料產生 React/Vue/HTML/Flutter 程式碼。"""
    ir_path = args.ir_file
    target = (args.target or "html").lower()
    output_dir = args.output or "./generated"

    if not os.path.exists(ir_path):
        print(f"❌ 找不到 IR 檔案：{ir_path}")
        return

    with open(ir_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 判斷是 IR 格式還是 .pen batch_get 格式
    if "version" in data and "tree" in data:
        # 已是 IR v2.0 格式
        ir_tree = data["tree"]
        page_name = args.page or data.get("source", {}).get("entryFile", "Page")
    elif isinstance(data, list) or "type" in data:
        # .pen batch_get 格式，需要轉換
        converter = PencilToIR(page_name=args.page or "Page")
        ir_doc = converter.convert(data)
        ir_tree = ir_doc["tree"]
        page_name = args.page or "Page"
    else:
        print("❌ 不支援的 JSON 格式。需要 IR v2.0 文件或 .pen batch_get 節點資料。")
        return

    try:
        result = generate_from_ir(
            ir_data=ir_tree,
            target=target,
            output_dir=output_dir,
            page_name=page_name,
            with_utility_css=args.with_utility_css,
        )
        files = result.get("files", [])
        print(f"✅ 已產生 {target} 專案至 {output_dir}（{len(files)} 個檔案）")
        for fp in files:
            print(f"   📄 {fp}")
    except Exception as e:
        print(f"❌ Codegen 失敗：{e}")


def cmd_pull(args, config: dict):
    """Pull: [DEPRECATED] 從 Figma 讀取 — 已棄用，請改用 codegen。"""
    print("⚠️  'pull' 命令已棄用。Figma 整合已移除。")
    print("   建議改用新工作流：")
    print("   1. 在 Pencil AI 中設計 UI")
    print("   2. 使用 batch_get 匯出節點 JSON")
    print("   3. pdm codegen <ir.json> --target vue")
    return


def cmd_generate(args, config: dict):
    """Generate: [DEPRECATED] 從 Figma 產生新前端 — 已棄用，請改用 codegen。"""
    print("⚠️  'generate' 命令已棄用。Figma 整合已移除。")
    print("   建議改用新工作流：")
    print("   pdm codegen <ir.json> --target react --output ./out")


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
        description="AiIRIS-pdm: Spec → Pencil AI → Fine-tune → React/Vue Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", "-c", default="pencil.config.json", help="Config path")
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

    pull_p = sub.add_parser("pull", help="[DEPRECATED] 已棄用 — 請改用 codegen")

    gen_p = sub.add_parser("generate", help="[DEPRECATED] 已棄用 — 請改用 codegen")

    # ── codegen：新工作流主力命令 ──
    codegen_p = sub.add_parser("codegen", help="IR/Pencil → React/Vue/HTML/Flutter",
        epilog="Examples:\n  pdm codegen .pdm/ir-payload.json --target react --output ./out\n  pdm codegen pen-export.json --target vue",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    codegen_p.add_argument("ir_file", help="IR v2.0 JSON 或 .pen batch_get 匯出的 JSON 檔案")
    codegen_p.add_argument("--target", choices=["react", "vue", "html", "flutter"], default="html", help="輸出目標")
    codegen_p.add_argument("--output", default="./generated", help="輸出目錄")
    codegen_p.add_argument("--page", help="Page name")
    codegen_p.add_argument("--with-utility-css", action="store_true", help="產出 utility.css")

    export_p = sub.add_parser("export-tokens", help="從 IR 產出 design tokens (tokens.json 或 CSS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  pdm export-tokens\n  pdm export-tokens --from-dir .pdm --output tokens.json --format css")
    export_p.add_argument("--from-dir", default=".pdm", help="IR 目錄（內含 figma-import-payload.json）")
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
    elif args.command == "codegen":
        cmd_codegen(args, config)
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
