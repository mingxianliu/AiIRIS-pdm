# WebMCP 與 AiIRIS-pdm 整合評估

> 評估 [WebMCP](https://github.com/erich/webmcp)（Web Model Context Protocol 提案）對 AiIRIS-pdm 的幫助與取捨。

---

## 一、WebMCP 是什麼

- **定位**：讓**網頁**以 JavaScript 暴露「工具」（具描述與 schema 的函數），供 **AI 代理**或**瀏覽器助理**呼叫，實現人機協作、同一個 web 介面共享情境。
- **運作方式**：網站在 `window.navigator.modelContext` 註冊 tools（name、description、inputSchema、execute）；**連到該頁的 agent** 可呼叫這些工具。
- **前提**：必須有 **browsing context**（例如已開啟的瀏覽器分頁）。提案明確寫明：**目前不支援 headless／無可見瀏覽器 UI 的情境**（"no support for agents ... to call tools headlessly"）。
- **典型情境**：使用者在設計網站開著頁面 → 請瀏覽器裡的 agent 幫忙 → agent 呼叫頁面註冊的 `filterTemplates(description)`、`editDesign(instructions)` 等，人與 agent 共用同一介面。

---

## 二、AiIRIS-pdm 在做什麼

- **Push**：用 **Playwright 無頭模式** 開一個 URL → 注入 **DOM_WALKER_V2_JS** → 擷取 DOM 樹與 computed styles → 建 IR → 寫出 JSON。全程 **headless、無使用者介面**，目標是**可重現**的 IR。
- **使用者**：開發者在本機跑 `figma-sync push <url>`，不需要「人在瀏覽器裡操作」。
- **被擷取的頁面**：可以是任意 Vue/React/HTML，**不必**實作任何 MCP 或工具；pdm 只讀 DOM 與樣式。

---

## 三、對齊與差異

| 維度 | WebMCP | AiIRIS-pdm (Push) |
|------|--------|---------------------|
| **執行環境** | 有 UI 的瀏覽器分頁，agent 連到該頁 | Headless browser，CLI 本機執行 |
| **頁面角色** | 主動註冊「工具」給 agent 呼叫 | 被動被擷取 DOM，無需改動 |
| **互動方式** | Agent 呼叫頁面 JS（例如 `editDesign(...)`） | 注入固定腳本讀 DOM，不呼叫業務邏輯 |
| **Headless** | 明確列為非目標 | 核心設計（無頭擷取） |
| **目標** | 人機協作、工具化既有 UI 能力 | Code→Figma 同步、產出確定性 IR |

---

## 四、對 pdm 有沒有幫助？

### 結論：**對目前 pdm 核心流程幾乎沒有直接幫助**

1. **Headless 與否**  
   pdm 的 Push 是 headless；WebMCP 假設「agent 連到已開啟的頁面」、不支援 headless 呼叫工具。要把 pdm 改成「開有頭瀏覽器＋等頁面註冊 WebMCP 工具」會偏離現有設計，且多數使用情境（CI、本機一鍵 push）不需要可見瀏覽器。

2. **職責不同**  
   WebMCP 是「網頁暴露**動作**（add-todo、editDesign）給 agent」；pdm 是「**讀取**任意頁面的 DOM／樣式並產出 IR」。pdm 不需要頁面提供「可呼叫的業務工具」，只需要可讀的 DOM。

3. **通用性**  
   pdm 的價值之一是**不需改動目標應用**即可對任何 URL 做 push。若改為依賴 WebMCP，只有「有實作 WebMCP 且暴露例如 `exportFigmaIR()` 的網站」才能用，反而縮小適用範圍。

### 理論上的「可選」情境（效益有限）

- 若**未來**某類應用主動提供 WebMCP 工具（例如 `getDesignSnapshot()` 回傳類 IR 結構），pdm **可選**在「偵測到該工具時」改走工具呼叫而非 DOM walk。但：
  - 目前沒有這類標準或實作；
  - 會增加分支邏輯與維護成本；
  - 現有 DOM 擷取已能涵蓋絕大多數頁面，優先級低。

---

## 五、建議

| 問題 | 建議 |
|------|------|
| **是否整合 WebMCP 到 pdm 主線？** | **不建議**。情境與設計（headless vs 有 UI、讀取 vs 工具呼叫）不一致，整合成本高、收益低。 |
| **是否在文件裡提及 WebMCP？** | 可選。在「與其他標準／協定」的說明中簡短註明：pdm 為 headless 擷取，與 WebMCP 之人機協作、頁面工具暴露為不同面向，目前無整合計畫。 |
| **若未來 WebMCP 支援 headless？** | 屆時再評估「可選地」呼叫頁面提供的 export 類工具；目前提案未往此方向，維持現狀即可。 |

---

*評估依據：webmcp README、proposal.md 與 AiIRIS-pdm Push 流程。*
