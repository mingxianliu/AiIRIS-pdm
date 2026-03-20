#!/usr/bin/env python3
"""
AiIRIS-pdm CLI — Spec → Pencil AI → Fine-tune → React/Vue Code

  aipdm push <url>                          # Code → IR snapshot
  aipdm watch <url>                         # Watch + auto push
  aipdm codegen <ir-json> --target vue      # IR → React/Vue/HTML/Flutter
  aipdm figmai import <figma-file.json> -o ui-ir.json   # REST File → UiIR
  aipdm figmai codegen ui-ir.json --target vue          # UiIR → 程式碼
  aipdm preview <url>                       # 預覽命名樹
  aipdm export-tokens                       # IR → design tokens
"""

import argparse
import asyncio
import json
import logging
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


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FIGMA_CONSOLE_RETRYABLE = 30
EXIT_FIGMA_CONSOLE_RESPONSE = 31
EXIT_FIGMA_CONSOLE_IMPORT = 32
EXIT_RUNTIME = 1


def _classify_console_exit_code(exc: Exception) -> int:
    from .figma_console_ws import FigmaConsoleResponseError, FigmaConsoleRetryableError

    if isinstance(exc, FigmaConsoleRetryableError):
        return EXIT_FIGMA_CONSOLE_RETRYABLE
    if isinstance(exc, FigmaConsoleResponseError):
        return EXIT_FIGMA_CONSOLE_RESPONSE
    if isinstance(exc, ImportError):
        return EXIT_FIGMA_CONSOLE_IMPORT
    return EXIT_RUNTIME


def _add_rpc_retry_args(parser) -> None:
    parser.add_argument("--rpc-timeout", type=float, default=120.0, help="figma-console RPC timeout 秒數")
    parser.add_argument("--rpc-retries", type=int, default=0, help="figma-console RPC 重試次數")
    parser.add_argument("--rpc-backoff", type=float, default=0.25, help="figma-console RPC 指數退避起始秒數")
    parser.add_argument("--rpc-backoff-max", type=float, default=2.0, help="figma-console RPC 指數退避最大秒數")
    parser.add_argument("--trace-id", default=None, help="觀測用 trace id；省略則由底層自動產生")
    parser.add_argument("--verbose", action="store_true", help="輸出 figma-console / remote flow 詳細 timing log")


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
    print("   3. aipdm codegen <ir.json> --target vue")
    return


def cmd_generate(args, config: dict):
    """Generate: [DEPRECATED] 從 Figma 產生新前端 — 已棄用，請改用 codegen。"""
    print("⚠️  'generate' 命令已棄用。Figma 整合已移除。")
    print("   建議改用新工作流：")
    print("   aipdm codegen <ir.json> --target react --output ./out")


def cmd_figma_mai(args):
    """FigmAI 對齊：import / codegen / chain-local / flow。"""
    import json as _json
    from pathlib import Path as _Path

    from .figmai import (
        figma_api_file_to_ui_ir_document,
        load_ui_ir_tree_from_file_payload,
        run_chain_pipeline,
        run_chain_remote,
        run_flow_from_file_json,
        run_flow_via_console,
    )
    from .generator import generate_from_ir

    if args.fm_cmd == "import":
        path = _Path(args.json_file)
        if not path.is_file():
            print(f"❌ 找不到檔案：{path}")
            return EXIT_USAGE
        try:
            payload = _json.loads(path.read_text(encoding="utf-8"))
        except _json.JSONDecodeError as e:
            print(f"❌ JSON 解析失敗：{e}")
            return EXIT_USAGE
        try:
            doc = figma_api_file_to_ui_ir_document(
                payload,
                page_index=args.page_index,
                page_name=args.page_name,
                plugin_namespace=args.plugin_namespace,
            )
        except ValueError as e:
            print(f"❌ {e}")
            return EXIT_USAGE
        text = _json.dumps(doc, ensure_ascii=False, indent=2)
        if args.output:
            out = _Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            print(f"✅ UiIR 已寫入 {out.resolve()}")
        else:
            print(text)
        return EXIT_OK

    if args.fm_cmd == "codegen":
        path = _Path(args.ui_ir_file)
        if not path.is_file():
            print(f"❌ 找不到檔案：{path}")
            return EXIT_USAGE
        try:
            raw = _json.loads(path.read_text(encoding="utf-8"))
            tree = load_ui_ir_tree_from_file_payload(raw)
        except (ValueError, _json.JSONDecodeError, TypeError) as e:
            print(f"❌ 讀取 UiIR 失敗：{e}")
            return EXIT_USAGE
        from .figmai.ui_ir_to_airis import ui_ir_to_airis_ir

        airis_root = ui_ir_to_airis_ir(tree)
        if args.page:
            airis_root = {**airis_root, "figmaName": args.page}
        try:
            result = generate_from_ir(
                airis_root,
                target=args.target,
                output_dir=args.output,
                page_name=args.page,
                with_utility_css=args.with_utility_css,
            )
        except Exception as e:
            print(f"❌ codegen 失敗：{e}")
            return EXIT_RUNTIME
        print(f"✅ 已產生 {len(result.get('files', []))} 個檔案 → {result.get('output_dir')}")
        for rel in result.get("files", [])[:20]:
            print(f"   · {rel}")
        if len(result.get("files", [])) > 20:
            print("   · …")
        return EXIT_OK

    if args.fm_cmd == "chain-local":
        try:
            result = run_chain_pipeline(
                spec_path=args.spec_file,
                output_dir=args.output,
                target=args.target,
                with_utility_css=args.with_utility_css,
            )
        except Exception as e:
            print(f"❌ chain-local 失敗：{e}")
            return EXIT_RUNTIME
        print("✅ chain-local 完成")
        for st in result.get("stages", []):
            print(f"   · {st.get('name')}: {st.get('status')}")
        return EXIT_OK

    if args.fm_cmd == "chain":
        try:
            result = run_chain_remote(
                spec_path=args.spec_file,
                output_dir=args.output,
                target=args.target,
                host=args.host,
                port=args.port,
                depth=args.depth,
                sync=args.sync,
                figma_node_id=args.figma_node_id,
                with_utility_css=args.with_utility_css,
                state_dir=args.state_dir,
                missing_node_strategy=args.missing_node_strategy,
                rpc_timeout=args.rpc_timeout,
                rpc_retries=args.rpc_retries,
                rpc_retry_backoff_s=args.rpc_backoff,
                rpc_retry_backoff_max_s=args.rpc_backoff_max,
                trace_id=args.trace_id,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"❌ chain 失敗：{e}")
            return _classify_console_exit_code(e)
        print("✅ chain 完成")
        print(f"   · target_node_id: {result.get('target_node_id')}")
        if result.get("synced_root_id"):
            print(f"   · synced_root_id: {result.get('synced_root_id')}")
        if result.get("state_file"):
            print(f"   · state_file: {result.get('state_file')}")
        print(f"   · missing_node_strategy: {result.get('missing_node_strategy')}")
        print(f"   · deleted_count: {result.get('deleted_count', 0)}")
        print(f"   · orphaned_count: {result.get('orphaned_count', 0)}")
        print(f"   · output_dir: {result.get('output_dir')}")
        for rel in result.get("generated_files", [])[:20]:
            print(f"   · {rel}")
        if len(result.get("generated_files", [])) > 20:
            print("   · …")
        return EXIT_OK

    if args.fm_cmd == "flow":
        try:
            if args.live:
                manifest = run_flow_via_console(
                    output_dir=args.output,
                    host=args.host,
                    port=args.port,
                    pattern=args.pattern,
                    include=[s.strip() for s in (args.include or "").split(",") if s.strip()],
                    exclude=[s.strip() for s in (args.exclude or "").split(",") if s.strip()],
                    framework=args.framework,
                    fidelity=args.fidelity,
                    depth=args.depth,
                    notify=args.notify,
                    rpc_timeout=args.rpc_timeout,
                    rpc_retries=args.rpc_retries,
                    rpc_retry_backoff_s=args.rpc_backoff,
                    rpc_retry_backoff_max_s=args.rpc_backoff_max,
                    trace_id=args.trace_id,
                    verbose=args.verbose,
                )
            else:
                if not args.json_file:
                    print("❌ 離線模式需提供 json_file；或改用 --live。")
                    return EXIT_USAGE
                manifest = run_flow_from_file_json(
                    figma_file_json_path=args.json_file,
                    output_dir=args.output,
                    pattern=args.pattern,
                    framework=args.framework,
                    fidelity=args.fidelity,
                )
        except Exception as e:
            print(f"❌ flow 失敗：{e}")
            return _classify_console_exit_code(e)
        total = manifest.get("count")
        if total is None and isinstance(manifest.get("counts"), dict):
            total = manifest["counts"].get("generated", 0)
        if total is None:
            total = 0
        print(f"✅ flow 完成，共 {total} 頁")
        return EXIT_OK

    print(f"❌ 未知 figmai 子命令：{args.fm_cmd}")
    return EXIT_USAGE


def cmd_figma_console(args):
    """Figma Console WebSocket 代理：serve / request / bridge-path（純 Python）。"""
    import json as _json

    from .figma_console_ws import bridge_script_path, request_sync, run_server_blocking

    if args.fc_cmd == "serve":
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        run_server_blocking(host=args.fc_host, port=args.fc_port)
        return EXIT_OK
    elif args.fc_cmd == "request":
        try:
            params_obj = _json.loads(args.fc_params or "{}")
        except _json.JSONDecodeError as e:
            print(f"❌ --params 不是合法 JSON：{e}")
            return EXIT_USAGE
        try:
            result = request_sync(
                args.fc_method,
                params_obj if isinstance(params_obj, dict) else {},
                host=args.fc_host,
                port=args.fc_port,
                timeout=args.rpc_timeout,
                retries=args.rpc_retries,
                retry_backoff_s=args.rpc_backoff,
                retry_backoff_max_s=args.rpc_backoff_max,
                trace_id=args.trace_id,
                verbose=args.verbose,
            )
            print(_json.dumps(result, ensure_ascii=False, indent=2))
        except ImportError as e:
            print(f"❌ {e}")
            return _classify_console_exit_code(e)
        except Exception as e:
            print(f"❌ {e}")
            return _classify_console_exit_code(e)
        return EXIT_OK
    elif args.fc_cmd == "bridge-path":
        print(bridge_script_path())
        return EXIT_OK
    return EXIT_USAGE


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
        print("   請先執行 'aipdm push <url>' 產生 IR。")
    except Exception as e:
        print(f"❌ export-tokens 失敗: {e}")


def deprecated_main() -> None:
    """舊 console script `pdm`：改由 `aipdm` 為正式名稱，避免與 PyPA PDM 套件管理器衝突。"""
    print(
        "注意: 請改用 `aipdm` 作為指令名稱（`pdm` 仍暫留相容，但易與 PyPA 的 pdm 套件管理器混淆）。",
        file=sys.stderr,
    )
    main()


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
        epilog="Examples:\n  aipdm push http://localhost:5173\n  aipdm push http://localhost:5173 --viewport 375x812\n  aipdm push http://localhost:5173 --selector '#login-form'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    push_p.add_argument("url", help="App URL (e.g. http://localhost:5173)")
    push_p.add_argument("--viewport", help="WxH e.g. 375x812")
    push_p.add_argument("--root", help="Root selector (deprecated, use --selector)")
    push_p.add_argument("--selector", help="Partial sync: CSS selector to capture (e.g. '#login-form')")
    push_p.add_argument("--erslice", action="store_true", help="Write ErSlice manifest & completeness")
    push_p.add_argument("--erslice-module", default="default", help="Module name for manifest")
    push_p.add_argument("--erslice-page", default="page", help="Page slug for manifest")

    watch_p = sub.add_parser("watch", help="Watch for file changes and auto-push",
        epilog="Examples:\n  aipdm watch http://localhost:5173\n  aipdm watch http://localhost:5173 --viewport 375x812",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    watch_p.add_argument("url", help="App URL (e.g. http://localhost:5173)")
    watch_p.add_argument("--viewport", help="WxH e.g. 375x812")
    watch_p.add_argument("--root", help="Root selector (deprecated, use --selector)")
    watch_p.add_argument("--selector", help="Partial sync: CSS selector to capture (e.g. '#login-form')")
    watch_p.add_argument("--erslice", action="store_true", help="Write ErSlice manifest & completeness")
    watch_p.add_argument("--erslice-module", default="default", help="Module name for manifest")
    watch_p.add_argument("--erslice-page", default="page", help="Page slug for manifest")

    stories_p = sub.add_parser("push-stories", help="Batch sync from Storybook",
        epilog="Examples:\n  aipdm push-stories http://localhost:6006\n  aipdm push-stories http://localhost:6006 --filter 'Button'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    stories_p.add_argument("url", help="Storybook URL (e.g. http://localhost:6006)")
    stories_p.add_argument("--filter", help="Filter stories by name (regex)")

    preview_p = sub.add_parser("preview", help="Preview naming tree",
        epilog="Examples:\n  aipdm preview http://localhost:5173\n  aipdm preview http://localhost:5173 --selector '#sidebar'",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    preview_p.add_argument("url", help="App URL")
    preview_p.add_argument("--selector", help="CSS selector to preview (e.g. '#sidebar')")

    pull_p = sub.add_parser("pull", help="[DEPRECATED] 已棄用 — 請改用 codegen")

    gen_p = sub.add_parser("generate", help="[DEPRECATED] 已棄用 — 請改用 codegen")

    # ── codegen：新工作流主力命令 ──
    codegen_p = sub.add_parser("codegen", help="IR/Pencil → React/Vue/HTML/Flutter",
        epilog="Examples:\n  aipdm codegen .pdm/ir-payload.json --target react --output ./out\n  aipdm codegen pen-export.json --target vue",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    codegen_p.add_argument("ir_file", help="IR v2.0 JSON 或 .pen batch_get 匯出的 JSON 檔案")
    codegen_p.add_argument("--target", choices=["react", "vue", "html", "flutter"], default="html", help="輸出目標")
    codegen_p.add_argument("--output", default="./generated", help="輸出目錄")
    codegen_p.add_argument("--page", help="Page name")
    codegen_p.add_argument("--with-utility-css", action="store_true", help="產出 utility.css")

    export_p = sub.add_parser("export-tokens", help="從 IR 產出 design tokens (tokens.json 或 CSS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  aipdm export-tokens\n  aipdm export-tokens --from-dir .pdm --output tokens.json --format css")
    export_p.add_argument("--from-dir", default=".pdm", help="IR 目錄（內含 figma-import-payload.json）")
    export_p.add_argument("--output", "-o", default="tokens.json", help="輸出檔路徑")
    export_p.add_argument("--format", choices=["json", "css"], default="json", help="輸出格式")
    export_p.add_argument("--css-prefix", default="--token", help="CSS 變數前綴（僅 format=css 時使用）")

    fc = sub.add_parser(
        "figma-console",
        help="Figma Desktop Console WebSocket 橋（Python，不需 Node／figmai）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "流程：\n"
            "  1) aipdm figma-console serve\n"
            "  2) figma-console bridge-path → 將該 js 整段貼入 Figma Console\n"
            "  3) aipdm figma-console request getNode --params '{\"nodeId\":\"1:2\",\"depth\":2}'"
        ),
    )
    fc_sub = fc.add_subparsers(dest="fc_cmd", required=True)
    fc_s = fc_sub.add_parser("serve", help="啟動本機 WebSocket 代理（預設 3055）")
    fc_s.add_argument("--host", dest="fc_host", default="0.0.0.0", help="監聽位址")
    fc_s.add_argument("--port", dest="fc_port", type=int, default=3055, help="監聽埠")
    fc_r = fc_sub.add_parser("request", help="對 Figma 轉發一則 RPC（需已完成 serve + bridge）")
    fc_r.add_argument("fc_method", metavar="method", help="例如 getNode、getSelection、searchNodes")
    fc_r.add_argument("--params", dest="fc_params", default="{}", help='JSON 物件字串，預設 "{}"')
    fc_r.add_argument("--host", dest="fc_host", default="localhost", help="代理主機")
    fc_r.add_argument("--port", dest="fc_port", type=int, default=3055, help="代理埠")
    _add_rpc_retry_args(fc_r)
    fc_b = fc_sub.add_parser("bridge-path", help="顯示內建 figma_console_bridge.js 的絕對路徑")
    fc_b.set_defaults(fc_host=None, fc_port=None, fc_method=None, fc_params=None)

    fm = sub.add_parser(
        "figmai",
        help="FigmAI 對齊層：Figma file JSON → UiIR → codegen（純 Python）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "範例：\n"
            "  aipdm figmai import figma-export.json -o ui-ir.json\n"
            "  aipdm figmai codegen ui-ir.json --target vue --output ./out\n"
        ),
    )
    fm_sub = fm.add_subparsers(dest="fm_cmd", required=True)
    fm_imp = fm_sub.add_parser(
        "import",
        help="讀取 GET /v1/files/:key 匯出的 JSON，產出 UiIR（aipdm-ui-ir）",
    )
    fm_imp.add_argument("json_file", help="Figma File API JSON 路徑")
    fm_imp.add_argument("--page-index", type=int, default=0, help="頁面索引（預設第一頁）")
    fm_imp.add_argument("--page-name", default=None, help="若指定則依頁名選取，優先於 --page-index")
    fm_imp.add_argument("-o", "--output", default=None, help="輸出 UiIR 檔案；省略則印到 stdout")
    fm_imp.add_argument(
        "--plugin-namespace",
        default="figma-code-sync",
        help="sharedPluginData 命名空間（與 FigmaToIR 一致）",
    )
    fm_gen = fm_sub.add_parser(
        "codegen",
        help="由 UiIR JSON 還原 IR 並呼叫 generate_from_ir",
    )
    fm_gen.add_argument("ui_ir_file", help="figmai import 產物或含 tree 的 JSON")
    fm_gen.add_argument("--target", choices=["react", "vue", "html", "flutter"], default="html")
    fm_gen.add_argument("--output", "-o", default="./generated", help="輸出目錄")
    fm_gen.add_argument("--with-utility-css", action="store_true", help="產出 utility.css")
    fm_gen.add_argument("--page", default=None, help="覆寫單頁 IR 的顯示名稱（多為除錯用）")
    fm_chain = fm_sub.add_parser(
        "chain-local",
        help="完整 chain-local：spec -> design-ops -> UiIR -> codegen",
    )
    fm_chain.add_argument("spec_file", help="component spec JSON 路徑")
    fm_chain.add_argument("--target", choices=["react", "vue", "html", "flutter"], default="vue")
    fm_chain.add_argument("--output", "-o", default="./generated/chain", help="輸出目錄")
    fm_chain.add_argument("--with-utility-css", action="store_true", help="產出 utility.css")
    fm_remote = fm_sub.add_parser(
        "chain",
        help="完整 chain：連線 figma-console 拉取/同步後再 codegen（對齊舊 TS 命名）",
    )
    fm_remote.add_argument("spec_file", help="component spec JSON 路徑")
    fm_remote.add_argument("--figma-node-id", default=None, help="指定遠端節點 id（可覆寫 spec.meta.figmaNodeId）")
    fm_remote.add_argument("--sync", action="store_true", help="先把 spec design-ops 同步到 Figma，再以同步後節點拉取")
    fm_remote.add_argument("--host", default="localhost", help="figma-console 主機")
    fm_remote.add_argument("--port", type=int, default=3055, help="figma-console 埠")
    fm_remote.add_argument("--depth", type=int, default=8, help="getNode 深度")
    fm_remote.add_argument("--target", choices=["react", "vue", "html", "flutter"], default="vue")
    fm_remote.add_argument("--output", "-o", default="./generated/chain-remote", help="輸出目錄")
    fm_remote.add_argument("--state-dir", default=None, help="映射檔目錄（預設同 --output，檔名 state.json）")
    fm_remote.add_argument(
        "--missing-node-strategy",
        choices=["keep", "orphan", "delete"],
        default="orphan",
        help="當 state mapping 有、但 spec 已不存在時的處理策略",
    )
    fm_remote.add_argument("--with-utility-css", action="store_true", help="產出 utility.css")
    _add_rpc_retry_args(fm_remote)
    fm_flow = fm_sub.add_parser(
        "flow",
        help="批次頁面輸出（由 Figma file JSON 離線跑 flow）",
    )
    fm_flow.add_argument("json_file", nargs="?", default="", help="Figma File API JSON 路徑（離線模式必填）")
    fm_flow.add_argument("--output", "-o", default="./generated", help="輸出目錄")
    fm_flow.add_argument("--pattern", default="[Page]", help="頁面節點前綴")
    fm_flow.add_argument("--framework", choices=["vue", "react", "both"], default="both")
    fm_flow.add_argument("--fidelity", choices=["semantic", "pixel"], default="semantic")
    fm_flow.add_argument("--live", action="store_true", help="改走 figma-console live 模式（searchNodes/getNode）")
    fm_flow.add_argument("--host", default="localhost", help="figma-console 主機（live 模式）")
    fm_flow.add_argument("--port", type=int, default=3055, help="figma-console 埠（live 模式）")
    fm_flow.add_argument("--include", default="", help="名稱 include 關鍵字，逗號分隔（live 模式）")
    fm_flow.add_argument("--exclude", default="", help="名稱 exclude 關鍵字，逗號分隔（live 模式）")
    fm_flow.add_argument("--depth", type=int, default=8, help="getNode 深度（live 模式）")
    fm_flow.add_argument("--notify", action="store_true", help="完成後送 notify（live 模式）")
    _add_rpc_retry_args(fm_flow)

    args = parser.parse_args()

    # figma-console 不依賴 pencil.config.json，避免無 srcRoot 等無謂警告
    if args.command == "figma-console":
        raise SystemExit(cmd_figma_console(args))
    if args.command == "figmai":
        raise SystemExit(cmd_figma_mai(args))

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
