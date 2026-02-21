# AiIRIS-pdm 架構審查與 Token 說明

## 一、架構完整性審查

### 1. Push（Code → Figma）— ✅ 完整可行

| 環節 | 狀態 | 說明 |
|------|------|------|
| DOM 擷取 | ✅ | Playwright + 內嵌 DOM Walker，可擷取完整樣式（gradient、shadow、SVG、grid 等） |
| 命名引擎 | ✅ | data-figma-name → 組件 → id → class → fallback，與 config 對應 |
| IR 建構 | ✅ | 單一 ir_builder 產出 IR 2.0，含 layout、styles、pluginData |
| 寫出檔案 | ✅ | plugin-payload.json、figma-import-payload.json、name-mapping.json、screenshot |
| Figma Plugin | ✅ | 單一 code.js 讀 payload、建節點、寫 pluginData，建置通過 |

**結論**：Push 流程已用 `tests/fixtures/minimal.html` + 本地 server 跑通，產出可直接在 Figma 匯入。

---

### 2. Pull（Figma → Code）— ✅ 流程完整，需 Token

| 環節 | 狀態 | 說明 |
|------|------|------|
| 讀取 Figma 檔案 | ✅ | 透過 **Figma REST API**（需 Personal Access Token） |
| Figma → IR | ✅ | FigmaToIR 將 API 節點轉成 IR，供 diff |
| Diff | ✅ | IRDiffer 比對「push 時快照」與「目前 Figma」 |
| Patch 報告 | ✅ | CodePatcher 產出 Tailwind/CSS 建議 |
| --apply 回寫 | ⚠️ | 依 name_mapping 的 sourceFile；目前 sourceFile 多為 entryUrl（URL），非本機檔案路徑，故實際寫檔需 config 提供 srcRoot/檔案對應或後續擴充 |

**結論**：Pull 的「讀 Figma → diff → 報告」完整；真正把變更寫回原始檔（--apply）需確保 name_mapping 或 config 能解析出本機路徑（例如 entryUrl 對應到 srcRoot 的檔案），目前設計預留此擴充點。

---

### 3. 依賴與介面

- **Push**：僅需本機（Playwright、requests）；不需 Figma 帳號或 Token。
- **Figma Plugin**：在 Figma 內執行，讀取使用者選擇的 JSON 檔；不需 Token。
- **Pull**：必須能讀取 Figma 檔案 → 必須使用 **Figma API Token**（見下節）。

---

## 二、為什麼需要 Token？

### Token 只用於「Pull」，不用於 Push 或 Plugin

| 步驟 | 是否呼叫 Figma 伺服器 | 是否需要 Token |
|------|------------------------|----------------|
| **push** | 否（只開瀏覽器擷取你的 app URL，寫 JSON 到本機） | ❌ 不需要 |
| **Figma 匯入** | 否（Plugin 在 Figma 裡讀你選的 JSON 檔） | ❌ 不需要 |
| **pull** | 是（要從 Figma 把「檔案內容」抓下來） | ✅ **需要** |

### 技術原因

- **Figma REST API** 的 [Get file](https://www.figma.com/developers/api#get-files-endpoint) 是**受保護的**：  
  `GET https://api.figma.com/v1/files/:file_key` 必須帶 `X-Figma-Token` header。
- 不帶 Token 會得到 **403 Unauthorized**，無法讀取任何檔案（包含你自己建立的檔案）。
- Token 的取得方式：Figma 帳號 → Settings → Personal access tokens → 產生一組，複製後設成環境變數 `FIGMA_TOKEN` 或寫在 `figma-sync.config.json` 的 `figma.personalAccessToken`。

因此：  
**Token 只為了在「Pull」時，讓本機 CLI 有權限向 Figma 要檔案內容；Push 與在 Figma 裡匯入都不會用到 Token。**

---

## 三、架構圖（含 Token 使用處）

```
┌─────────────────────────────────────────────────────────────────┐
│  Push（不需 Token）                                                │
│  本機 URL → Playwright → DOM 樹 → IR → .figma-sync/*.json        │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Figma 內（不需 Token）                                            │
│  使用者選 plugin-payload.json → Plugin 建節點                     │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Pull（需要 Token）                                                │
│  FIGMA_TOKEN + file_key → Figma API GET /v1/files/:key           │
│  → FigmaToIR → diff(before_ir, after_ir) → Patch 報告 / --apply  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、建議與後續可補強點

1. **Pull --apply 與本機路徑**  
   - 目前 name_mapping 的 `sourceFile` 來自 config 的 `entryUrl`（多為 URL）。  
   - 若要做「直接改 Vue/React 檔」，可考慮：config 增加「URL → 本機路徑」對應，或由命名階段寫入實際檔案路徑，再讓 CodePatcher 依路徑寫檔。

2. **Token 安全**  
   - 建議僅用環境變數或本機 config，勿提交到版控；README 已說明，可再於 docs 加一筆「取得與設定 Token」簡短說明。

3. **錯誤處理**  
   - Pull 時若 Token 過期或 file_key 無權限，可明確提示「檢查 FIGMA_TOKEN 與 file key」。

---

*審查依據：AiIRIS-pdm 現有程式與 2026-02 流程驗證結果。*
