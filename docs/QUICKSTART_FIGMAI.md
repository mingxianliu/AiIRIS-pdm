# FigmAI Quickstart（chain / flow）

本頁提供一條「第一次跑通」最短路徑：只用 `aipdm` 的 Python 管線完成 `chain` 與 `flow`。

## 0) 前置

```bash
pip install -e ".[dev]"
pip install -e ".[figma-console]"  # 需要 websockets
```

> CI 目前保證 Python 3.10 / 3.11 / 3.12。若使用 3.9，請先在本機自行驗證。

## 1) 啟動 figma-console（本機代理）

```bash
# Terminal A
aipdm figma-console serve --host 0.0.0.0 --port 3055
```

```bash
# Terminal B：取得 bridge 路徑
aipdm figma-console bridge-path
```

將 bridge JS 整段貼到 Figma Desktop Console（Plugins > Development > Open Console）。

## 2) 快速健康檢查

```bash
aipdm figma-console request searchNodes --params '{"query":"[Page]"}'
```

成功回應 JSON 代表代理、bridge、RPC 路徑正常。

## 3) 跑 chain（remote）

```bash
# 讀取現有節點並產碼
aipdm figmai chain ./component-spec.json \
  --figma-node-id "1:2" \
  --host localhost --port 3055 \
  --target vue \
  --output ./generated/chain-remote
```

```bash
# 先同步 spec 再拉回產碼（idempotent）
aipdm figmai chain ./component-spec.json \
  --sync \
  --state-dir ./.figmai-state \
  --missing-node-strategy orphan \
  --host localhost --port 3055 \
  --target react \
  --output ./generated/chain-remote
```

## 4) 跑 flow（live）

```bash
aipdm figmai flow \
  --live \
  --host localhost --port 3055 \
  --pattern "[Page]" \
  --framework both \
  --fidelity semantic \
  --include login,register \
  --exclude draft \
  --output ./generated/flow-live
```

## 5) 常用重試參數（網路不穩時）

`figma-console request`、`figmai chain`、`figmai flow --live` 皆支援：

- `--rpc-timeout`
- `--rpc-retries`
- `--rpc-backoff`
- `--rpc-backoff-max`

範例：

```bash
aipdm figmai chain ./component-spec.json \
  --sync \
  --rpc-timeout 180 \
  --rpc-retries 3 \
  --rpc-backoff 0.5 \
  --rpc-backoff-max 3 \
  --host localhost --port 3055 \
  --target vue
```

## 6) 驗證與回歸

```bash
python3 -m pytest \
  tests/test_figmai_nightly_parity.py \
  tests/test_figmai_golden_parity.py \
  tests/test_figmai_golden_expanded.py \
  tests/test_output_matrix.py \
  tests/test_figma_console_ws.py \
  -q

python3 scripts/diff_against_baseline.py
```

若你需要更完整的維運與排障，請看 `docs/FIGMA_CONSOLE_OPS.md`。
