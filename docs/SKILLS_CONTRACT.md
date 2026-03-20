# FigmAI Skills Contract

本文件定義 `airis_pdm/figmai/skills/` 既有 skill 的輸入契約、輸出形狀、錯誤策略與 golden 維護方式。TASK 3 的封閉條件是：現有 skill 全部有文件、golden 與測試，之後若新增 skill，視為新任務。

## 錯誤策略

- leaf skill 與 generator skill 一律先驗證 `ui_ir_root`
- `ui_ir_root` 不是 `dict`，或任一層 `children` 不是 `list`，一律拋出 `SkillContractError`
- 缺少非必要欄位時採固定預設：
  - root `name` 預設 `"Component"`
  - root `sourceType` 預設 `"FRAME"`
  - 任一層缺少 `children` 時視為空陣列
- `AllInOneSkill` 先套同一份 root 驗證；若某個子 skill 執行失敗，不吞掉整體結果，而是把錯誤收斂到 `errors[skill_name] = {"type", "message"}`

## Golden 維護

- leaf skill golden：`tests/golden/skills_leaf_contracts.json`
- aggregate / generator golden：`tests/golden/skills_aggregate_contracts.json`
- 矩陣 golden（多 fixture）：`tests/test_figmai_skills_golden.py` 對應 `tests/golden/skills_*_*.json`
- **重新產生 leaf／aggregate 契約檔**（與 `test_figmai_skills.py` 邏輯一致）：
  ```bash
  python scripts/regenerate_skills_contract_goldens.py
  ```
- 更新流程：
  1. 先確認行為變更是有意的產品決策
  2. 修改 skill 與測試
  3. 更新 golden JSON（必要時跑上列腳本）
  4. 執行 `python3 -m pytest tests/test_figmai_skills.py tests/test_figmai_skills_golden.py -q`
  5. 在 PR 與 `CHANGELOG.md` 說明哪個 skill 契約變更、原因是什麼

## Skills

### `AnatomySkill`

- 做什麼：走訪 UiIR 樹，輸出非 root 圖層的順序、名稱、型別與基礎座標
- 不做什麼：不推導互動、可選狀態或複雜語意；`isOptional` 目前固定為 `false`

### `ApiSpecSkill`

- 做什麼：從 `metadata.componentProperties` 輸出屬性列表，鍵名排序固定為字母序
- 不做什麼：不推導 API 呼叫、資料來源、事件 payload；非布林值一律視為字串屬性

### `ColorAnnotationSkill`

- 做什麼：蒐集節點 `styles.backgroundColor`，輸出 token annotation 形狀
- 不做什麼：不分析 gradient、image fill、hover/active state，也不做 token 對映猜測

### `PropertiesSkill`

- 做什麼：從節點名稱中的 `Key=Value` 片段萃取 variant axes，並固定排序
- 不做什麼：不解析布林 toggle 與 Figma component set 全量變體；沒有 `=` 的名稱片段會被忽略

### `StructureSkill`

- 做什麼：輸出高度、spacing、padding 與單一圓角摘要，作為結構基線
- 不做什麼：不重建完整 auto layout 規則，也不描述多 variant 尺寸矩陣

### `ScreenReaderSkill`

- 做什麼：優先使用第一個可讀文字作為 label，輸出 VoiceOver、TalkBack、ARIA 的固定結構
- 不做什麼：不推導實際平台 accessibility tree，也不輸出自訂 action handler

### `AllInOneSkill`

- 做什麼：聚合既有分析型 skill，回傳合併後 `spec`、各 skill markdown 與錯誤摘要
- 不做什麼：不包含 React/Vue generator skill，也不保證其中一個子 skill 失敗時整批中止

### `ReactGeneratorSkill`

- 做什麼：把 UiIR 轉回 codegen IR，再呼叫 `generate_from_ir(..., target="react")`
- 不做什麼：不保證檔名策略以外的產物內容契約；產物 parity 由 TASK 1 負責

### `VueGeneratorSkill`

- 做什麼：把 UiIR 轉回 codegen IR，再呼叫 `generate_from_ir(..., target="vue")`
- 不做什麼：不保證檔名策略以外的產物內容契約；產物 parity 由 TASK 1 負責
