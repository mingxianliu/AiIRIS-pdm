# Figma Console Smoke Record

> 狀態：`Pending real execution`
>
> 本文件是 **真機 smoke 成功紀錄模板**。只有在實際於 self-hosted macOS runner 或本機 Figma Desktop 環境執行成功後，才能將狀態改為 `Passed` 並補齊證據。不得用推測或 mock 結果填寫。

## 1. 執行摘要

- 狀態：`Pending real execution`
- 執行日期：
- 執行人：
- 執行環境：
  - runner / 主機名稱：
  - macOS 版本：
  - Python 版本：
  - `aipdm` commit SHA：
- Figma Desktop：
  - 版本：
  - 檔案名稱：
  - 是否已手動貼入 `figma_console_bridge.js`：`yes / no`

## 2. Smoke 參數

- host：
- port：
- search pattern：
- smoke node id：
- rpc timeout：
- rpc retries：
- rpc backoff：
- rpc backoff max：
- trace id：

## 3. 執行指令

```bash
aipdm figma-console serve --host ... --port ...

aipdm figma-console request searchNodes --params '...'

aipdm figma-console request getNode --params '...'
```

## 4. 結果

### `searchNodes`

- 退出碼：
- 是否成功：
- 回傳摘要：

### `getNode`

- 退出碼：
- 是否成功：
- 回傳摘要：

## 5. Artifact

最小診斷包應附：

- `metadata.json`
- `command-lines.txt`
- `prerequisites.txt`
- `proxy.log`
- `searchNodes.json`
- `getNode.json`

填寫：

- artifact 路徑或 workflow run 連結：
- 是否已檢查無 secrets：`yes / no`

## 6. 判定

- 本次 smoke 是否符合 TASK 4 最低要求（`searchNodes` + `getNode` 成功一次）：`yes / no`
- 若否，阻塞原因：
- 若是，是否可作為 TASK 4 成功紀錄：`yes / no`

## 7. 備註

- 問題 / 異常：
- 後續建議：
