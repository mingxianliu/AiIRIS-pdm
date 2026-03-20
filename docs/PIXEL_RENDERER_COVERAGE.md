# Pixel Renderer（`pixel_react` / `pixel_vue`）能力表

共用實作：`airis_pdm/figmai/renderers/pixel_common.py`。  
目標：從 Figma 節點形狀產出 **絕對定位 + CSS**，供 flow「pixel」模式與測試對拍；**非**完整 Figma 彩現引擎。

## 已支援（有測試或 golden）

| 類別 | Figma／JSON 欄位 | CSS 對應 | 備註 |
|------|------------------|----------|------|
| 版面 | `absoluteBoundingBox` | `position:absolute; left/top/width/height` | 相對根節點原點 |
| 根 | 根節點 bbox | `.pixel-root { position:relative; … }` | |
| 填色 | `fills[]` 單一 `SOLID` | `background-color` 或 TEXT 的 `color` | 含 `fill.opacity` |
| 填色 | `GRADIENT_LINEAR` / `GRADIENT_RADIAL` | `linear-gradient` / `radial-gradient` | 簡化角度 |
| 填色 | 多層 `fills`（非 TEXT） | `background: 層1, 層2, …` | 底層在前、頂層在後（已對齊 Figma 順序） |
| 填色 | `IMAGE` + `imageUrl` | `background: url(…) center / cover no-repeat` | |
| 填色 | `IMAGE` 無 URL | `rgba(170,170,170,0.35)` 占位 | 不猜測本機 hash |
| 透明度 | `opacity`（節點） | 與 fill／effect 的 alpha **相乘** | |
| 陰影 | `effects[]` 多個 `DROP_SHADOW` | `box-shadow: …, …` | 可見的皆輸出 |
| 描邊 | `strokes` + `strokeWeight` | `border` 或 `outline` | `INSIDE`→border；`OUTSIDE`→outline |
| 圓角 | `cornerRadius` | `border-radius` | |
| 圓角 | `rectangleCornerRadii` | `border-radius: tl tr br bl` | |
| 混合 | `blendMode`（fill 或節點） | `mix-blend-mode` | 僅 `MULTIPLY`、`SCREEN`；其餘略過 |
| 裁切 | `FRAME` + `clipsContent` | `overflow:hidden` | |
| 可見 | `visible: false` | `visibility:hidden` | 仍輸出 DOM，僅隱藏 |
| 文字 | `characters`、`fontSize`、`fontName`、`letterSpacing`、`lineHeight` | 對應 typography | 與既有 golden 一致 |

## 明確不支援（不靜默「假裝一致」）

- 未列在上表的 `blendMode`（例如 `OVERLAY`、`COLOR_BURN` 等）— **不輸出** `mix-blend-mode`。
- `IMAGE` 僅認 `imageUrl`；Figma 僅有 `imageHash`／無 URL 時— **占位灰**，不嘗試解析本機資源。
- 向量路徑、自動版面約束、component 變體、plugin 自訂資料— **忽略**。
- 多層 **TEXT** 的複合 fill— **僅使用第一層**（與單層文字行為一致）。
- 對上述不支援能力，renderer 會在輸出的 CSS/style 區塊加入 `figmai-pixel warning: ...` 註解，避免靜默假一致。

## Golden／測試

- `tests/golden/pixel_*.json`：梯度、陰影、文字、多陰影、描邊圓角、多層 fill、圖片、混合／裁切／隱藏。
- `tests/test_figmai_golden_expanded.py`、`tests/test_figmai_pixel_coverage.py`。

## 相關文件

- Figma Console 本機代理與 RPC：[`FIGMA_CONSOLE_OPS.md`](FIGMA_CONSOLE_OPS.md)
- Baseline／parity：[`SNAPSHOT_PARITY_PROCESS.md`](SNAPSHOT_PARITY_PROCESS.md)

## 變更流程

新增「宣稱支援」的視覺屬性時，請：

1. 在 **本表** 新增列。  
2. 加 **fixture** + **React／Vue 斷言**。  
3. 更新 `CHANGELOG.md`（Unreleased）。
