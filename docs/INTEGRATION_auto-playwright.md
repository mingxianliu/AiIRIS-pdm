# auto-playwright 與 AiIRIS-pdm 整合評估

> 評估 [auto-playwright](https://github.com/lucgagan/auto-playwright) 整合到 AiIRIS-pdm 的價值與取捨。

---

## 一、兩邊在做什麼

| 維度 | auto-playwright | AiIRIS-pdm（Push） |
|------|-----------------|---------------------|
| **語言／執行環境** | TypeScript / Node，npm 套件 | Python，pip 套件 |
| **Playwright 用途** | 用 **AI（OpenAI）** 解讀自然語言，驅動 browser 做查詢、操作、斷言 | **規則固定**：`page.goto(url)` + 注入 **DOM_WALKER_V2_JS**，擷取 DOM 樹與樣式 |
| **目標** | 測試／自動化：用一句話讓 AI 找元素、點擊、填表、檢查結果 | 設計同步：產出**可重現**的 IR JSON（結構 + 樣式）給 Figma |
| **輸出** | 查詢結果、動作是否成功、斷言 true/false | `plugin-payload.json`、`figma-import-payload.json`、截圖 |
| **依賴** | OpenAI API（付費）、`@playwright/test` | 僅 Playwright（Python）、本機執行 |

---

## 二、整合價值評估

### 直接整合進 Python 管線：**價值低**

- **技術棧不同**：auto-playwright 是 Node/TS、依賴 OpenAI；AiIRIS-pdm 是 Python、目前無 AI 呼叫。要「整合」等於在 Python 裡呼叫 Node 腳本或重寫一套「AI + Playwright」邏輯，成本高。
- **職責不同**：Push 需要的是**確定性、可重現**的 DOM 快照（同一 URL、同一 viewport → 同一 IR）。AI 驅動的步驟（例如「點這裡、再點那裡」）本質上較不穩定，不適合當成 IR 產出的核心。
- **依賴與成本**：auto-playwright 需要 `OPENAI_API_KEY` 與呼叫費用；Push 目前零 API、本機即可跑，整合會增加門檻與成本。

### 作為「可選前處理」：**有情境、但非必要**

- **情境**：例如「先登入、開到某頁、再對該頁做 Push」。理論上可用 auto-playwright 在 Node 裡用 AI 導航到目標狀態（登入、點到 dashboard），再讓 AiIRIS-pdm 對**同一瀏覽器／同一 session** 做擷取——但這需要兩邊共用 browser/session 或透過固定 URL + cookie，實作與維護成本高。
- **替代做法**：用 Playwright 或 pdm 的 config（例如 `wait_for_selector`、多步 goto）或自己寫一小段腳本導航到目標頁，再對該 URL 做 `figma-sync push`，通常就夠用，且可重現、不依賴 AI。

---

## 三、結論與建議

| 問題 | 結論 |
|------|------|
| **有沒有整合價值？** | **核心 Push 管線**：幾乎沒有。兩邊目標與技術棧都不同，硬整合成本高、收益低。 |
| **適合當「可選工具」嗎？** | 僅在「必須用 AI 導航到複雜狀態再擷取」時才有想像空間；多數情境用現有 Playwright 設定或小腳本即可。 |
| **建議** | **不把 auto-playwright 整合進 AiIRIS-pdm 主線**。若未來有「AI 導航後再 Push」的需求，可單獨做一個**外部腳本**（Node 跑 auto-playwright → 導到目標 URL / 匯出 cookie → Python 用同一 session 跑 push），與 pdm 解耦，文件裡註明為選用流程即可。 |

---

*評估依據：auto-playwright README / 程式與 AiIRIS-pdm dom_extractor 用途比較。*
