# Migration Task Status Summary

本文件整理目前四條 migration 任務線的剩餘清單、完成度與是否可宣告封閉。目的是把「還剩什麼」寫成固定清單，避免後續反覆出現口頭追加。

## 總表

| TASK | 目前完成度 | 主要已完成 | 剩餘清單 | 是否可封 |
|------|-----------|-----------|---------|---------|
| TASK 1 產物級 Parity | 80～90% | chain-local / chain-remote(mock) / flow / manifest / router / parity matrix / baseline 文件已存在 | 再確認 baseline 覆蓋範圍是否已被團隊正式接受；若還有未納入 target 或 fixture，要補 golden；若要更嚴格，可再補更多 idempotent 案例 | 接近可封 |
| TASK 2 Pixel Renderer | 65～85% | 已有 pixel fixture、golden、coverage 文件，部分屬性已補齊 | 需逐項對照封頂清單，確認每個屬性都有 fixture + golden + 文件勾選；若有支援限制但文件未寫清，也算未封 | 可能未封 |
| TASK 3 Skills | 90～95% | contract 文件、leaf/generator/all-in-one 測試、golden、統一錯誤策略已完成 | 若要更保守，只剩每個 skill 再補更多獨立命名的 edge fixture；主幹契約已齊 | 可封或接近可封 |
| TASK 4 整合 / 韌性 / 維運 | 70～80% | timeout / retry / backoff、CLI exit code 分類、runbook、手動真機 smoke workflow 骨架、artifact 診斷包固定集合已完成 | 還缺更完整真機軌道驗證與成功紀錄、TASK 4 結案條件再明文化 | 尚未可封 |

## TASK 1 — 產物級 Parity

### 已完成

- `tests/golden/` 已作為權威 baseline 使用
- chain-local / chain-remote(mock) / flow / manifest / router 已有 parity 測試
- baseline 更新流程已寫入 `docs/SNAPSHOT_PARITY_PROCESS.md`

### 剩餘

- 確認目前 baseline 覆蓋範圍已被團隊正式接受
- 若仍有未入列 target、fixture 或 hot path，補入 golden
- 若要更硬，補更多「同輸入兩次產出 0 diff」案例

### 封閉判定

- 團隊接受現有 `tests/golden/` 範圍就是 TASK 1 的封閉範圍：可封
- 若還有未列入但被認定屬於既有 scope 的產物熱點：未封

## TASK 2 — Pixel Renderer

### 已完成

- 已有多組 pixel fixture 與 golden
- 已有 coverage 文件
- React / Vue pixel 產物已有部分共用規則與回歸測試

### 剩餘

- 逐項核對封頂清單，而不是憑印象判斷
- 每一項能力需具備：
  - fixture
  - React / Vue golden
  - 文件勾選或限制說明
- 清單外能力需明確標示不支援

### 封閉判定

- 若封頂清單已逐項對完且文件齊：可封
- 若仍存在「看起來做了，但沒有 fixture / 文件 / 限制說明」：未封

## TASK 3 — Skills

### 已完成

- `docs/SKILLS_CONTRACT.md`
- leaf skill / generator skill / all-in-one 測試
- golden contracts
- 一致錯誤策略 `SkillContractError`

### 剩餘

- 可選補強：每個 skill 再補 1～2 個獨立 edge fixture
- 可選補強：generator skill 再補更細的邊界樣本

### 封閉判定

- 以目前 contract + golden + tests 作為驗收標準：可封
- 若團隊要求「每個 skill 都需更多獨立 edge fixture」才算結案：接近可封，但未完全封

## TASK 4 — 整合 / 韌性 / 維運

### 已完成

- figma-console request timeout / retry / backoff
- CLI console error exit code 分類
- `docs/FIGMA_CONSOLE_OPS.md`
- 手動真機 smoke workflow 骨架
- smoke artifact 診斷包固定集合

### 剩餘

- 補 `verbose` / trace id / step timing
- 把真機 smoke 從「骨架」提升到「有一次可重現成功紀錄」
- 將「TASK 4 結案條件」寫成硬性條款

### 封閉判定

- 目前仍未封
- 若要封，至少需補齊觀測性、真機驗證紀錄與結案條件文件

### 結案條件

TASK 4 要結案，至少需滿足：

1. mock 韌性測試全齊
2. 預設 CI 不依賴真 Figma
3. `trace-id` / `verbose` / timing log 已落地
4. 真機 smoke 軌道與主 CI 分離
5. 診斷包固定
6. 至少一份可重現真機成功紀錄（可用 `docs/reports/FIGMA_CONSOLE_SMOKE_RECORD_TEMPLATE.md` 填寫）
7. `docs/FIGMA_CONSOLE_OPS.md` 可獨立指導執行與排障

## 優先順序建議

若目標是盡快讓整體 migration 進入封閉狀態，建議優先順序如下：

1. TASK 4：把韌性與維運補到可驗收
2. TASK 2：逐條核對 pixel 封頂清單
3. TASK 1：取得團隊對 baseline 範圍的正式 signoff
4. TASK 3：只做可選加固，不阻塞結案

## 一句話結論

- 最接近封閉的是 TASK 3
- 最不確定的是 TASK 2，因為必須看封頂清單是否真的逐項對表
- 最明確尚未封的是 TASK 4
- 若要全案收尾，優先處理 TASK 4
