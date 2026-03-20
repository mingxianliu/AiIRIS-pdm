## 變更摘要

- [ ] 說明本次修改的目標與範圍
- [ ] 說明是否影響 `figmai` chain/flow/pixel/skills/ir_contract

## 測試結果

- [ ] `python -m pytest tests/test_figmai_nightly_parity.py -v --tb=short`
- [ ] `python -m pytest tests/test_figmai_golden_parity.py tests/test_figmai_golden_expanded.py -v --tb=short`
- [ ] `python -m pytest tests/test_output_matrix.py -v --tb=short`
- [ ] `python scripts/diff_against_baseline.py`（若涉及 chain/flow/codegen）
- [ ] 其他相關測試：

## Snapshot / Golden（若有）

> 若本 PR 涉及 `tests/golden/` 或 `tests/golden/nightly/`，本區為必填。

- [ ] 我已確認只提交匿名化後快照（無真實識別資料）
- [ ] 我已附上 anonymizer 前後 diff 摘要（遮罩規則與主要變更）
- [ ] 我已附上 golden 變更說明（哪些檔案、為何更新、預期差異）

### Anonymizer 前後 diff 摘要

<!-- 範例：字串遮罩數量、關鍵欄位是否增減 -->

### Golden 變更說明

<!-- 範例：fixture A 新增 routePath；fixture B 調整 collisions 預期 -->

## 風險與回滾

- [ ] 已說明已知風險
- [ ] 已提供回滾/修復策略（若 parity 失敗）
