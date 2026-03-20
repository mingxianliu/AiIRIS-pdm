# Snapshot 更新流程規範（Nightly Parity）

本文件規範「真實專案輸入快照（匿名化）」與 golden parity 的更新流程，確保每次變更可審核、可回歸、可追溯。

## 0. 權威 Baseline 宣告

> **本倉庫的唯一權威 baseline 為 `tests/golden/` 目錄。**
>
> 舊 TS 版本的 `out/` 產物目錄已不再作為對拍來源。所有 chain-local、chain-remote（mock）、flow（離線／live）、codegen 的預期輸出，均以本倉 `tests/golden/` 內的 fixture 為準。
>
> **理由**：舊 TS 版移除後，無法保證其產物可重現；本倉 golden 經 CI 每日驗證（`nightly-parity.yml`），變更必走 PR 審查，是可溯源的唯一事實來源。

### Baseline 與 CI 的關係

| 環節 | 位置 | 執行時機 |
|------|------|---------|
| Golden fixtures | `tests/golden/` | 隨 repo 提交，PR 審查 |
| Pytest parity suite | `test_output_matrix.py` + `test_figmai_golden_parity.py` + `test_figmai_golden_expanded.py` + `test_figmai_nightly_parity.py` +（nightly 另含 skills／pixel／`figma_console_ws`／`chain_remote`／`ir_contract`） | 每次 push/PR（`ci.yml` 跑全 `tests/`） + 每日排程（`nightly-parity.yml` 見 workflow） |
| Baseline diff report | `scripts/diff_against_baseline.py` | 每日排程（`nightly-parity.yml`） + 手動 |
| PR 審查護欄 | `.github/PULL_REQUEST_TEMPLATE.md` | 每個 golden 相關 PR |
| Figma Console 運維／除錯 | [`FIGMA_CONSOLE_OPS.md`](FIGMA_CONSOLE_OPS.md) | 本機 bridge、RPC 重試、退出碼、故障排除 |

### 為何不採用「舊 TS 匯出目錄」作為 baseline

| 方案 | 優點 | 缺點 | 結論 |
|------|------|------|------|
| A. 舊 TS `out/` 打包進 repo 或 submodule | 完全對齊舊版行為 | TS 已移除，無法重跑驗證；產物含大量二進位／時間戳雜訊；repo 體積膨脹；維護成本高 | **不採用** |
| B. 舊 TS `out/` 作為 CI artifact 下載 | 不佔 repo 空間 | 依賴外部 artifact 存活；無法在本地重現 CI；TS 側不再維護 | **不採用** |
| C. 本倉 `tests/golden/` 凍結目錄 | 可重現、可審查、CI 每次驗證、變更走 PR | 需手動從舊 TS 產物萃取初始 fixture | **採用（現行方案）** |

**決策記錄**：2026-03-20 確認方案 C。舊 TS 產物的語意已由 `tests/golden/` 內的 fixture 捕捉（manifest 鍵序、router 字面格式、檔案樹結構、RPC 序列）。若未來發現 golden 未涵蓋的舊 TS 行為，應補 fixture 進 `tests/golden/` 而非引入外部目錄。

### Baseline 在 CI 中的強制執行

| CI 工作流 | 執行內容 | 觸發條件 |
|-----------|---------|---------|
| `ci.yml` (test job) | `pytest tests/`（含 `test_output_matrix.py`）+ `scripts/diff_against_baseline.py` | 每次 push 到 main/dev、每個 PR |
| `nightly-parity.yml` | 4 個 parity test 檔 + `scripts/diff_against_baseline.py` | 每日 02:00 UTC + 手動 |

兩個 workflow 都會跑 `diff_against_baseline.py`，**任一失敗即 CI 紅燈**。不存在「nightly 才跑 baseline 檢查」的漏洞。

## 1. 適用範圍

以下任一情況都必須走本流程：

- 調整 `figmai` 的轉換/生成邏輯（chain、flow、pixel、ir_contract、skills）
- 更新 `tests/golden/` 或 `tests/golden/nightly/` 下任何 fixture
- 變更會影響 parity 測試輸出的欄位或排序

## 2. 快照更新原則

- **先匿名化再入庫**：不得提交未匿名化的真實資料。
- **保結構、去識別**：保留節點結構、型別、路徑語意；遮罩可識別字串。
- **最小變更**：只更新必要 fixture，避免一次改動過多基準資料。

## 3. 實作步驟

1. 準備原始快照（本機，不提交）
2. 透過 `anonymize_snapshot()` 產生匿名化 JSON
3. 將匿名化結果寫入 `tests/golden/nightly/*.json`
4. 執行 parity 測試
5. 比對更新前後差異並整理變更說明

## 4. 建議指令

```bash
# 1) 跑完整 parity suite（與 nightly CI 一致）
python -m pytest \
  tests/test_figmai_nightly_parity.py \
  tests/test_figmai_golden_parity.py \
  tests/test_figmai_golden_expanded.py \
  tests/test_output_matrix.py -v --tb=short

# 2) 跑 baseline diff 報告（與 nightly CI 一致）
python scripts/diff_against_baseline.py

# 3) 跑 figmai 全套（與擴充後 nightly 對齊時可加上 skills / pixel / ws）
python -m pytest tests/test_figmai*.py tests/test_output_matrix.py tests/test_figma_console_ws.py -q
```

## 5. PR 必備內容

每個涉及快照/golden 的 PR，說明中必須包含：

- **Anonymizer 前後 diff 摘要**
  - 例如：遮罩字串數量、主要欄位是否新增/刪除
- **Golden 變更說明**
  - 哪些 fixture 改了、為什麼要改、預期行為差異
- **測試證據**
  - `test_figmai_nightly_parity.py` 與相關 golden 測試皆通過

## 6. 審查檢查點（Reviewer）

- 是否有未匿名化字串、URL、內部識別資訊
- `expected` 區塊是否與實際產物一致且合理
- 變更是否只影響預期範圍（避免不相關 golden 漂移）
- CI/Nightly parity 是否可重現通過

## 7. 回滾策略

若 nightly parity 出現非預期漂移：

1. 先鎖定最近一次變更的 fixture/邏輯
2. 用同一份匿名快照重跑本地測試確認可重現
3. 若屬 regression，優先修程式；避免直接改 golden 掩蓋問題

## 8. Baseline 更新 SOP（TASK 1 — 產物級 Parity）

### 8.1 何謂「權威 baseline」

本倉以 `tests/golden/` 目錄作為凍結 baseline。所有 chain-local、chain-remote（mock）、flow（離線／live）的產物預期輸出均以 golden fixture 鎖定。

### 8.2 對拍維度

| 維度 | 說明 | 測試位置 |
|------|------|---------|
| 目錄相對路徑集合 | chain-local 各 target 的檔案樹 | `test_output_matrix.py::test_chain_local_file_tree_*` |
| 指定檔案完整文字 | manifest.json、router.ts/tsx 逐字比對 | `test_golden_parity.py` + `test_output_matrix.py` |
| 正規化後比對 | manifest 鍵序排序、include/exclude 排序、page row 鍵序 | `test_output_matrix.py::test_manifest_*` |
| 位元組級冪等 | 同一輸入兩次產出 0 diff | `test_output_matrix.py::test_codegen_*_idempotent` |
| RPC 序列 | chain-remote mock 的方法呼叫順序 | `test_output_matrix.py::test_chain_remote_golden_*` |
| state.json schema | 必要鍵與型別 | `test_output_matrix.py::test_chain_remote_state_json_schema` |

### 8.3 如何更新 baseline

1. **確認變更為有意為之的產品行為變更**（非 bug），在 PR 說明中載明原因。
2. 修改 `tests/golden/` 下對應的 fixture 檔案。
3. 執行全部 parity 測試：
   ```bash
   python -m pytest tests/test_output_matrix.py tests/test_figmai_golden_parity.py \
     tests/test_figmai_golden_expanded.py tests/test_figmai_nightly_parity.py -v --tb=short
   ```
4. 執行 baseline diff 報告（CI nightly 也會跑，本地先確認）：
   ```bash
   python scripts/diff_against_baseline.py
   ```
5. PR 必須附上 golden 變更說明與測試全綠截圖。

> **注意**：`scripts/diff_against_baseline.py` 已納入 `nightly-parity.yml` CI，若 diff 非零退出則 CI 失敗。

### 8.4 誰能改 golden

- 任何人可提 PR，但 golden 變更必須有至少一位 reviewer 審核。
- Reviewer 需確認：變更對應產品行為、無不相關漂移、CI 全綠。

### 8.5 CHANGELOG 要求

baseline／golden 變更必須在 CHANGELOG 中有一條對應說明。

### 8.6 封閉聲明

**何時算「parity 封閉」**：baseline 更新 ＝ 有意為之的產品行為變更。TASK 1 的 DoD 勾滿後，不再追加「順便」產物項；新增框架／新 CLI 行為 ＝ 新任務。

### 8.7 允許 diff 的白名單規則

以下差異在對拍時被正規化排除，不算失敗：

- 時間戳欄位（`started_at`、`finished_at`、`lastSync`）
- 產物中的絕對路徑（`output_dir`、`state_file`）

上述規則寫死在測試中，不可口頭約定。
