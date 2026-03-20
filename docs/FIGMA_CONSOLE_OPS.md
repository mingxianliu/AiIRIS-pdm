# Figma Console（figma-console）運維與除錯

本文件補齊 **TASK 4**：本機 WebSocket 代理、Figma 內 bridge、RPC 重試、常見故障與退出碼。與 **產物 parity**（TASK 1）無關；後者見 [`SNAPSHOT_PARITY_PROCESS.md`](SNAPSHOT_PARITY_PROCESS.md)。

## 架構（三元件）

| 元件 | 角色 | 說明 |
|------|------|------|
| **`aipdm figma-console serve`** | 本機 WebSocket 伺服器 | 預設 `0.0.0.0:3055`，轉發 JSON-RPC |
| **`figma_console_bridge.js`** | Figma Desktop **Console** 內執行 | `aipdm figma-console bridge-path` 取得路徑，整段貼入 Console |
| **CLI／figmai** | 客戶端 | `figma-console request`、`figmai chain`、`figmai flow --live` 皆透過 `request_sync` 連代理 |

依賴：`pip install -e ".[figma-console]"` 或 `pip install websockets>=12`。

## 標準操作流程（SOP）

1. **終端機 A**：啟動代理  
   `aipdm figma-console serve`  
   （可改 `--host 127.0.0.1 --port 3055`）

2. **Figma**：開啟目標檔 → **Plugins → Development** 或 **Console**（依你環境）→ 貼上 bridge 腳本並執行（腳本會連回 `ws://localhost:3055`）。

3. **終端機 B**：探測 RPC  
   ```bash
   aipdm figma-console request ping --params '{}' --host localhost --port 3055
   ```
   或使用 `getNode` / `searchNodes` 等（見 `airis_pdm/assets/figma_console_bridge.js` 支援表）。

4. **FigmAI 管線**（可選）：  
   - `aipdm figmai chain ./spec.json --figma-node-id "1:2" --host localhost --port 3055`  
   - `aipdm figmai flow --live --host localhost --port 3055 --pattern "[Page]"`

## RPC 逾時與重試

| 參數 | 預設 | 說明 |
|------|------|------|
| `--rpc-timeout` | `120` | 單次 WebSocket 往返逾時（秒） |
| `--rpc-retries` | `0` | 額外重試次數（總嘗試 = 1 + retries） |
| `--rpc-backoff` | `0.25` | 指數退避起始延遲（秒） |
| `--rpc-backoff-max` | `2.0` | 退避上限（秒） |
| `--trace-id` | 自動產生 | 觀測用 trace id，可把同一輪 smoke / chain / flow 的 log 串起來 |
| `--verbose` | `false` | 輸出 RPC 與 chain/flow summary timing log |

**會重試**：`TimeoutError`、`OSError`、`ConnectionError`、訊息含 `timeout`／`connection reset` 等（見 `figma_console_ws._is_retryable_console_error`）。

**不會重試**：JSON-RPC 回傳的 `error`（應用層錯誤）— 重試無法修復錯誤 method／參數。

### `trace-id` / `verbose`

若要讓同一輪 smoke / chain / flow 的 log 可追蹤，建議顯式給 `--trace-id` 並開 `--verbose`。

範例：

```bash
aipdm figma-console request getNode \
  --params '{"nodeId":"0:1","depth":2}' \
  --trace-id smoke-20260320-1 \
  --verbose
```

在 `--verbose` 模式下，會額外輸出：

- request start / success / retrying / failed / response-error
- `elapsed_ms`
- `figmai flow live completed ...`
- `figmai chain remote completed ...`

常見 log 欄位：

| 欄位 | 說明 |
|------|------|
| `trace_id` | 同一輪操作的識別碼 |
| `method` | RPC 方法名稱 |
| `attempt` | 第幾次嘗試 |
| `elapsed_ms` | 單次 RPC 或整體 flow/chain 耗時 |
| `matched` / `filtered` / `generated` | flow live summary |
| `deleted` / `orphaned` / `files` | chain remote summary |

範例（不穩網路或 Figma 偶發延遲）：

```bash
aipdm figma-console request getNode \
  --params '{"nodeId":"0:1","depth":2}' \
  --rpc-retries 3 --rpc-backoff 0.5 --rpc-backoff-max 4 \
  --trace-id smoke-retry-1 --verbose

aipdm figmai chain ./spec.json --figma-node-id "1:2" \
  --host localhost --port 3055 --rpc-retries 2 \
  --trace-id chain-run-1 --verbose
```

## CLI 退出碼（`aipdm figma-console request`）

| 碼 | 意義 |
|----|------|
| `0` | 成功 |
| `1` | 一般執行期錯誤 |
| `2` | 參數／用法錯誤（例如 `--params` 非合法 JSON） |
| `30` | `FigmaConsoleRetryableError`（逾時／連線類，重試耗盡） |
| `31` | `FigmaConsoleResponseError`（RPC 回傳 error） |
| `32` | 缺少 `websockets`（`ImportError`） |

自動化腳本可依 `30` 決定是否排程重跑整條命令。

## 常見問題（Troubleshooting）

| 現象 | 可能原因 | 建議 |
|------|----------|------|
| `Connection refused` | 未先 `serve` 或埠錯 | 確認終端機 A 正在跑、CLI `--port` 與 bridge 一致 |
| 一直逾時 | Figma 未開檔、bridge 未連上、外掛被擋 | 確認 Console 無紅字；必要時重貼 bridge |
| `method not supported` | bridge 版本舊或未實作該 RPC | 對照 `figma_console_bridge.js` 的 `switch (method)` |
| `ImportError: websockets` | 未裝可選依賴 | `pip install -e ".[figma-console]"` |
| `chain`／`flow --live` 空結果 | `searchNodes` 無匹配、或 pattern 與 frame 命名不符 | 檢查節點名稱是否以前綴（如 `[Page]`）開頭 |
| 想知道哪次 request 慢 | 沒開觀測 log | 加 `--trace-id ... --verbose`，看 `elapsed_ms` 與 summary log |

## 與 CI 的關係

- **公開 CI**（`ci.yml`）：**不**連真實 Figma；以 `pytest` mock 驗證 `chain_remote`、`flow`、`figma_console_ws` 行為。
- **可選真機 smoke**（團隊內部）：在本機或 **自架 runner**（含 Figma Desktop）執行上文 SOP；**勿**把 Figma token／帳密寫進公開 workflow。可直接參考 `.github/workflows/figma-console-smoke-manual.yml` 這份手動骨架。

## 診斷包（Artifact Bundle）

手動 smoke workflow 的 artifact 內容已固定。最小診斷包必須包含以下檔案：

| 檔案 | 用途 |
|------|------|
| `metadata.json` | 本次 workflow/run 的固定中繼資料與輸入參數 |
| `command-lines.txt` | 實際執行的命令列範本 |
| `prerequisites.txt` | runner / Figma Desktop / bridge 前置假設 |
| `proxy.log` | 本機代理 stdout/stderr |
| `proxy.pid` | 代理 PID，供 stop step 使用 |
| `searchNodes.json` | `searchNodes` smoke 原始輸出 |
| `getNode.json` | `getNode` smoke 原始輸出 |

規則：

- artifact 內不得包含 token、帳密、cookie 或其他 secrets
- `searchNodes.json` / `getNode.json` 保留原始 JSON 輸出，方便事後比對
- 若 workflow 失敗，仍必須上傳完整診斷包

這份固定集合的目的是讓每次 smoke 失敗時，reviewer 至少能回答：

1. 當時是用什麼參數執行
2. 代理有沒有正常啟動
3. `searchNodes` 與 `getNode` 各自回了什麼
4. 問題比較像環境、bridge，還是 RPC 本身

## 相關文件

- Baseline／golden／parity：[`SNAPSHOT_PARITY_PROCESS.md`](SNAPSHOT_PARITY_PROCESS.md)  
- Pixel 能力邊界：[`PIXEL_RENDERER_COVERAGE.md`](PIXEL_RENDERER_COVERAGE.md)  
- Skills 契約：[`SKILLS_CONTRACT.md`](SKILLS_CONTRACT.md)  
- Migration 收尾總表：[`TASK_STATUS_SUMMARY.md`](TASK_STATUS_SUMMARY.md)  
- 真機 smoke 成功紀錄模板：[`reports/FIGMA_CONSOLE_SMOKE_RECORD_TEMPLATE.md`](reports/FIGMA_CONSOLE_SMOKE_RECORD_TEMPLATE.md)  
- Bridge 原始碼：`airis_pdm/assets/figma_console_bridge.js`  
- Python 實作：`airis_pdm/figma_console_ws.py`
- 手動真機 smoke workflow：`.github/workflows/figma-console-smoke-manual.yml`

## TASK 4 結案條件（Definition of Done）

TASK 4 要宣告結案，至少需同時滿足以下條件：

1. **mock 韌性測試全齊**
   - timeout 至少 1 例
   - retry 成功至少 1 例
   - response error 不重試至少 1 例
   - CLI exit code 分類至少 1 例

2. **預設 CI 不依賴真 Figma**
   - `ci.yml` 與一般 `pytest` 路徑只跑 mock / local tests
   - 不要求 Figma Desktop、bridge、帳密或 secrets

3. **觀測性最低配已存在**
   - 支援 `--trace-id`
   - 支援 `--verbose`
   - request / retry / summary timing log 可輸出

4. **真機 smoke 軌道存在且與主 CI 分離**
   - 至少有一份手動或私有 workflow/runbook
   - 不把 flaky 真機檢查塞進預設 CI

5. **診斷包固定**
   - artifact bundle 至少包含本文件定義的最小集合
   - 失敗時仍上傳診斷包

6. **有一次可重現的真機成功紀錄**
   - 可接受形式：
     - workflow run 連結
     - 內部 wiki/runbook 截圖或紀錄
     - PR 說明中的成功執行證據
   - 最低要求是 `searchNodes` + `getNode` smoke 成功一次

7. **文件完成**
   - 本文件存在並可指導新成員完成本機或 runner smoke
   - 退出碼、重試旗標、診斷包內容、故障排查皆有說明

### TASK 4 封閉聲明

當以上條件全部滿足後，TASK 4 視為封閉。之後若要新增：

- 更高階 observability
- dashboard / 指標系統
- 更完整自動化真機矩陣
- SLO / 多機 / 多區部署

都屬新的 SRE / 平台任務，不再算進本次 migration 補缺。
