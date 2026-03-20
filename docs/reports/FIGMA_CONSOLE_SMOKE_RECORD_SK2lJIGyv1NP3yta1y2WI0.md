# Figma Console Smoke Record

> 狀態：`Pending real execution`
>
> 本文件尚未包含真機成功證據。請在 self-hosted macOS 或本機 Figma Desktop 環境實際跑通後，再把狀態改為 `Passed` 並補齊結果。

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
  - file key：`SK2lJIGyv1NP3yta1y2WI0`
  - node id：`0:1`
  - 是否已手動貼入 `figma_console_bridge.js`：`yes / no`

## 2. Smoke 參數

- host：`localhost`
- port：`3055`
- search pattern：`[Page]`
- smoke node id：`0:1`
- rpc timeout：`20`
- rpc retries：`2`
- rpc backoff：`0.5`
- rpc backoff max：`2.0`
- trace id：`smoke-figma-getnode`

## 3. 執行指令

```bash
aipdm figma-console serve --host 0.0.0.0 --port 3055

aipdm figma-console request ping \
  --params '{}' \
  --host localhost \
  --port 3055 \
  --trace-id smoke-figma-ping \
  --verbose

aipdm figma-console request getNode \
  --params '{"nodeId":"0:1","depth":1}' \
  --host localhost \
  --port 3055 \
  --rpc-timeout 20 \
  --rpc-retries 2 \
  --rpc-backoff 0.5 \
  --rpc-backoff-max 2.0 \
  --trace-id smoke-figma-getnode \
  --verbose
```

可選：

```bash
aipdm figma-console request searchNodes \
  --params '{"pattern":"[Page]"}' \
  --host localhost \
  --port 3055 \
  --rpc-timeout 20 \
  --rpc-retries 2 \
  --rpc-backoff 0.5 \
  --rpc-backoff-max 2.0 \
  --trace-id smoke-figma-search \
  --verbose
```

```bash
aipdm figmai flow --live \
  --host localhost \
  --port 3055 \
  --pattern "[Page]" \
  --framework vue \
  --fidelity semantic \
  --rpc-timeout 20 \
  --rpc-retries 2 \
  --rpc-backoff 0.5 \
  --rpc-backoff-max 2.0 \
  --trace-id smoke-figma-flow \
  --verbose
```

## 4. 結果

### `ping`

- 退出碼：
- 是否成功：
- 回傳摘要：

### `getNode`

- 退出碼：
- 是否成功：
- 回傳摘要：
- 是否取得 `nodeId = 0:1`：

### `searchNodes`（可選）

- 退出碼：
- 是否成功：
- 回傳摘要：

### `flow --live`（可選）

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

- 本次 smoke 是否符合 TASK 4 最低要求（`searchNodes` + `getNode` 成功一次，或至少 `getNode(nodeId=0:1)` 成功一次）：`yes / no`
- 若否，阻塞原因：
- 若是，是否可作為 TASK 4 成功紀錄：`yes / no`

## 7. 備註

- 問題 / 異常：
- 後續建議：
