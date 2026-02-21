# AiIRIS-pdm 與 ErSlice 對齊說明

本文件說明 AiIRIS-pdm 如何與 [ErSlice](https://github.com/openclaw/ErSlice) 的設計資產流程對齊，方便在 ErAI 生態中與 ErSlice 並用或後續整合。

## 概念對應

| ErSlice 概念 | AiIRIS-pdm 對應 |
|-------------|-----------------|
| design-assets 目錄結構 | 可選 `--erslice` 寫出 `erslice-manifest.json`、`completeness.json` 至輸出目錄 |
| 模組 / 頁面 / slug | `--erslice-module`、`--erslice-page` 寫入 manifest |
| 設計 Token | `design_assets.extract_design_tokens_from_ir()` 可從 IR 擷取顏色、字級，供 tokens.css / tokens.merge.json |
| Figma 雙向、保留階層 | IR 樹狀結構與 `figmaName` 一致；Figma Plugin 依 IR 建立節點並寫入 pluginData，pull 時依 nameMapping 回寫 |
| 切版說明包 | push 產出（IR、screenshot、name-mapping）可視為「程式碼快照」，與 ErSlice 的 html/css/ai-spec 互補 |

## 建議目錄對齊

若希望與 ErSlice 的 `design-assets/<module>/pages/<slug>/` 一致，可：

1. 在設定或 CLI 指定輸出目錄為 `design-assets/<module>/pages/<slug>/`。
2. 執行 push 時加上 `--erslice --erslice-module <module> --erslice-page <slug>`。
3. 該目錄下會得到：
   - `figma-import-payload.json`（完整 IR）
   - `plugin-payload.json`（Figma Plugin 用）
   - `name-mapping.json`
   - `reference-screenshot.png`
   - `erslice-manifest.json`
   - `completeness.json`

## 設計 Token

```python
from airis_pdm.design_assets import extract_design_tokens_from_ir

# 從已載入的 IR 樹擷取
tokens = extract_design_tokens_from_ir(ir_doc["tree"])
# tokens["colors"], tokens["fontSizes"], tokens["fontFamilies"]
```

可將 `tokens` 寫入 ErSlice 風格的 `tokens.css` 或 `tokens.merge.json`，供設計系統或 ErSlice 使用。

## Figma Plugin

AiIRIS-pdm 產出的 IR 與 [figma-code-sync](https://github.com/erich/figma-code-sync) 的 IR 格式相容，可直接使用該專案的 Figma Plugin 匯入 `plugin-payload.json`。Plugin 會依 `figmaName` 建立圖層並寫入 `sharedPluginData`，以利 pull 時 diff 與回寫。

## 參考

- ErSlice README：設計資產結構、Figma 匯入／匯出、Sketch 生成
- figma-code-sync README：IR schema、命名優先順序、Push/Pull 流程
