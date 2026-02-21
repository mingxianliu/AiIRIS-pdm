# Figma Plugin — Code-to-Figma Sync (AiIRIS-pdm)

本目錄為 Figma 外掛，用於載入 AiIRIS-pdm `push` 產出的 `plugin-payload.json`，在 Figma 中建立對應節點並保留命名與 pluginData（供 pull 回寫）。

## 建置

需先產生 `dist/code.js` 與 `dist/ui.html`：

```bash
cd figma_plugin
npm install   # 可選：僅需 TypeScript
npx tsc src/code.ts --outDir dist
cp src/ui.html dist/
```

或使用 npm script（若已加入 package.json）：

```bash
npm run build
```

## 安裝到 Figma

1. 在 Figma 桌面版：Plugins → Development → Import plugin from manifest...
2. 選擇本目錄下的 `manifest.json`（建置後需能讀取到 `dist/code.js` 與 `dist/ui.html`）。
3. 之後在 Plugins → Development 中執行「Code-to-Figma Sync (AiIRIS-pdm)」。

## 使用

1. 在專案根目錄執行 `python -m airis_pdm.cli push http://localhost:5173`，產生 `.figma-sync/plugin-payload.json`。
2. 在 Figma 開啟外掛，於 Import 分頁載入該 JSON（拖放或貼上）。
3. 點「Preview Names」檢查命名樹，再點「Import to Figma」建立圖層。
4. Export 分頁可匯出選取 frame 的節點樹（含 pluginData），供除錯或回寫對照。

## 相容性

Plugin 使用的 `sharedPluginData` 命名空間為 `figma-code-sync`，與 figma-code-sync 及 AiIRIS-pdm 的 pull 流程相容。
