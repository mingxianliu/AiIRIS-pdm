# 程式流程再確認 — export-tokens 與 hub workflow

> 從進入點到檔案讀寫 / 子流程的**程式呼叫鏈**。

---

## 一、figma-sync export-tokens（本機 pdm CLI）

```
進入點
  airis_pdm/cli.py :: main()
    args = parser.parse_args()
    args.command == "export-tokens"
    → cmd_export_tokens(args)

cmd_export_tokens(args)
  → token_export.export_tokens(
        ir_path_or_dir=args.from_dir,   # 預設 ".figma-sync"
        output_path=args.output,        # 預設 "tokens.json"
        format=args.format,             # "json" | "css"
        css_prefix=args.css_prefix,
    )

token_export.export_tokens()
  1. 解析 IR 路徑
      若 ir_path_or_dir 是目錄 → ir_path = <dir>/figma-import-payload.json
      否則 → ir_path = ir_path_or_dir（直接當檔案）
  2. 若檔案不存在 → raise FileNotFoundError
  3. 讀取 IR
      with open(ir_path) → json.load() → ir_doc
  4. 萃出 tokens
      tokens = extract_tokens_from_ir(ir_doc)
  5. 寫出
      format == "css" → tokens_to_css(tokens, prefix) → 寫入 output_path
      else → json.dump(tokens, output_path)
  6. return os.path.abspath(output_path)
```

**extract_tokens_from_ir(ir_doc)**（token_export.py）

```
  tree = ir_doc.get("tree")
  若無 "tree" 但有 "children" 或 "styles" → tree = ir_doc（單一節點相容）
  _collect_tokens_from_node(tree, out)   # 遞迴

_collect_tokens_from_node(node, out)
  • styles.fills[].type=="SOLID" → out["colors"].append(color)
  • styles.backgroundColor → out["colors"]
  • node.text → color, fontSize, fontFamily, fontWeight, lineHeight → out["typography"]
  • node.autoLayout.spacing → out["spacing"]
  • for child in node.children → _collect_tokens_from_node(child, out)
  最後對 fontSizes / fontWeights / lineHeights / spacing 排序
  return out
```

---

## 二、figma-sync push（產出 IR，供 export-tokens 讀）

```
main()
  args.command == "push"
  → asyncio.run(cmd_push(args, config))

cmd_push()
  → asyncio.run(perform_push(args.url, args, config))

perform_push(url, args, config)
  1. process_url_to_ir(url, args, config)
       → extract_dom_tree(url, ExtractionConfig(...))   # dom_extractor，Playwright）
       → build_ir_from_extraction(result, config)        # ir_builder，產 ir_doc
       return (ir_doc, result)
  2. output_dir = config.export.snapshotDir || ".figma-sync"
  3. save_ir(ir_doc, output_dir)   # ir_builder.save_ir

save_ir(ir_doc, output_dir)
  • <output_dir>/figma-import-payload.json  ← 整份 ir_doc（含 version, source, viewport, nameMapping, tree）
  • <output_dir>/name-mapping.json
  • <output_dir>/plugin-payload.json        ← 僅 ir_doc["tree"]
  return (ir_path, mapping_path)
```

故 **export-tokens** 讀的即是 **push** 寫入的 `figma-import-payload.json`。

---

## 三、hub workflow（aiiris workflow phase5 | phase7 | phase10）

```
進入點
  hub/cli/main.py :: workflow_command(phase, path, run)
  _ensure_plugins_loaded()
  phase 正規化 → "phase5-prototype" | "phase7-figma-refine" | "phase10-backfill"
```

### Phase 5（只看說明 或 --run 產 tokens）

```
  console.print(WORKFLOW_PHASE5_GUIDE)
  if run:
    plugin = _get_plugin_or_exit("pdm")
    result = asyncio.run(plugin.handle_command("pdm.export_tokens", {"path": path}))
    # 依 result.success 印 output 或 error
```

### Phase 7（只看說明 或 --run 執行 pull）

```
  console.print(WORKFLOW_PHASE7_GUIDE)
  if run:
    file_key = os.environ.get("FIGMA_FILE_KEY") or config_manager.get("plugins", {}).get("pdm", {}).get("figma_file_key")
    if not file_key → 印警告並 typer.Exit(1)
    plugin.handle_command("pdm.pull", {"file_key": file_key, "apply": True})
```

### Phase 10（只看說明 或 --run 產 tokens）

```
  console.print(WORKFLOW_PHASE10_GUIDE)
  if run:
    plugin.handle_command("pdm.export_tokens", {"path": path})
```

---

## 四、hub → pdm plugin 的指令分派

```
plugins/pdm/plugin.py :: handle_command(command, args)

  command == "pdm.export_tokens"
    → await self._pdm_export_tokens(args)

  command == "pdm.pull"
    → await self._pdm_pull(args)
```

**_pdm_export_tokens(args)**（plugin 內）

```
  path = Path(args.get("path", ".")).resolve()
  from_dir = args.get("from_dir", ".figma-sync")
  output = args.get("output", "tokens.json")
  fmt = args.get("format", "json")

  if from_dir == ".figma-sync":
    ir_dir = path / ".figma-sync"
    out_path = path / output（若 output 非絕對）
  else:
    ir_dir = Path(from_dir).resolve()
    out_path = 絕對或 path / output

  cmd = [python_command, "-m", "airis_pdm.cli",
         "export-tokens", "--from-dir", str(ir_dir), "--output", str(out_path), "--format", fmt]
  result = subprocess.run(cmd, cwd=self.pdm_path, capture_output=True, text=True)
  return { "success": result.returncode == 0, "output": result.stdout, "error": result.stderr }
```

即：hub 的 **pdm.export_tokens** 是透過 **subprocess 再跑一次 figma-sync（python -m airis_pdm.cli export-tokens）**，工作目錄為 plugin 的 `self.pdm_path`，IR 與輸出路徑用參數傳成絕對路徑（path 來自 `aiiris workflow --path`）。

**_pdm_pull(args)**（plugin 內）

```
  file_key = args.get("file_key")
  apply_changes = args.get("apply", False)
  cmd = [python_command, "-m", "airis_pdm.cli", "pull", "--file-key", file_key]
  if apply_changes: cmd.append("--apply")
  result = subprocess.run(cmd, cwd=self.pdm_path, ...)
  return { success, output, error }
```

---

## 五、資料流總覽

```
[ 使用者 ]
    │
    ├─ figma-sync push <url>
    │     → dom_extractor.extract_dom_tree()
    │     → ir_builder.build_ir_from_extraction()
    │     → ir_builder.save_ir()
    │     → .figma-sync/figma-import-payload.json（+ name-mapping.json, plugin-payload.json）
    │
    ├─ figma-sync export-tokens
    │     → token_export.export_tokens()
    │     → 讀 .figma-sync/figma-import-payload.json
    │     → extract_tokens_from_ir() → _collect_tokens_from_node() 遞迴
    │     → tokens.json 或 .css
    │
    └─ aiiris workflow phase5-prototype --run
          → hub main workflow_command()
          → plugin.handle_command("pdm.export_tokens", { path })
          → plugin._pdm_export_tokens()
          → subprocess: python -m airis_pdm.cli export-tokens --from-dir <path/.figma-sync> --output <path/tokens.json>
          → 同上 token_export 流程（在子行程）
```

---

## 六、關鍵檔案對照

| 步驟 | 讀取 | 寫入 |
|------|------|------|
| push | （無，從 URL 擷取 DOM） | `.figma-sync/figma-import-payload.json`, `name-mapping.json`, `plugin-payload.json`, `reference-screenshot.png` |
| export-tokens | `.figma-sync/figma-import-payload.json`（或 --from-dir 指定） | `tokens.json`（或 --output / --format css） |
| pull | `.figma-sync/figma-import-payload.json`（本地快照）+ Figma API | diff 報告；--apply 時依 config.source.srcRoot 改寫原始碼 |

程式流程上，**push 寫入的 IR** 是 **export-tokens 與 pull 的輸入**；hub 的 workflow --run 只是用 subprocess 呼叫同一套 pdm CLI，並用 `--path` 決定專案目錄下的 `.figma-sync` 與 `tokens.json` 路徑。
