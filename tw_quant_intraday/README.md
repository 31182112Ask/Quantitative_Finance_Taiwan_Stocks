# tw_quant_intraday

`tw_quant_intraday` 是台股短期交易與日內交易的本地研究輔助工具。第一版聚焦：

- T+1 Swing 日資料策略
- Opening Range Breakout 盤中策略
- 成本、滑價、價差、延遲成本估算
- 風控審核、倉位大小、kill-switch 條件
- 回測、紙上交易、報告
- 僅輸出人工下單清單

## 不自動下單聲明

本專案不提供、也不應新增以下功能：

- 券商登入
- APP 自動點擊
- 自動送出委託
- 讀取簡訊、OTP、憑證或帳密
- 儲存券商帳號密碼
- 任何形式的自動交易機器人

實盤輔助模式只能輸出：

- `reports/intraday/manual_order_ticket.csv`
- `reports/intraday/manual_order_ticket.md`

使用者必須自行開啟券商 APP、自行輸入委託、自行確認送出。

## 安裝

```bash
cd tw_quant_intraday
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

測試：

```bash
pytest
```

若本機 pytest 外掛造成結束時卡住，可用：

```bash
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q
```

## 資料來源設定

資料欄位遵守 `AGENTS.md` 的標準 schema。日資料預設讀取：

```text
data/daily/daily.csv
```

盤中資料預設讀取：

```text
data/intraday/YYYY-MM-DD_STOCKID.csv
```

若沒有穩定盤中資料，系統只會使用本地 CSV 或明確標記的 mock/demo data。mock/demo data 不是真實即時行情，不可作為實盤依據。

建立示範日資料：

```bash
python -m src.cli fetch-daily --mock
```

建立可交易股票池：

```bash
python -m src.cli build-universe
```

輸出：

```text
data/processed/universe.csv
reports/daily/market_summary.md
```

## 回測

T+1 Swing 回測：

```bash
python -m src.cli backtest --strategy t_plus_one_swing
```

輸出：

```text
reports/daily/backtest_trades.csv
reports/daily/backtest_equity_curve.csv
reports/daily/performance.md
```

Opening Range Breakout 第一版主要用於盤中掃描與訊號測試；日線回測命令目前以 T+1 Swing 為主。

## Benchmark：2026-05 台股策略全執行測試

抓取 TWSE 官方公開日資料。T+1 Swing 需要 60 日均線，所以 benchmark 會抓 2026-01-01 起的前置歷史，再只評估 2026-05-01 到 2026-05-31 的訊號：

```bash
python -m src.cli fetch-twse-daily --stocks 2330 2317 --start 2026-01-01 --end 2026-05-31 --output data/daily/twse_2026_05_benchmark.csv
```

10,000 TWD 零股/逐股模擬：

```bash
python -m src.cli benchmark --data-file data/daily/twse_2026_05_benchmark.csv --start 2026-05-01 --end 2026-05-31 --initial-cash 10000 --lot-size 1 --label benchmark_odd_lot_202605
```

10,000 TWD 整張 1000 股模擬：

```bash
python -m src.cli benchmark --data-file data/daily/twse_2026_05_benchmark.csv --start 2026-05-01 --end 2026-05-31 --initial-cash 10000 --lot-size 1000 --label benchmark_board_lot_202605
```

輸出：

```text
reports/daily/benchmark_odd_lot_202605_report.md
reports/daily/benchmark_odd_lot_202605_trades.csv
reports/daily/benchmark_odd_lot_202605_equity_curve.csv
reports/daily/benchmark_board_lot_202605_report.md
```

Benchmark 拒絕使用 mock data，除非明確加上 `--allow-mock`。

## 紙上交易

紙上交易不連接券商、不送單，只使用本地虛擬帳戶：

```bash
python -m src.cli paper-run
```

輸出：

```text
reports/paper_trading/trades.csv
reports/paper_trading/equity_curve.csv
reports/paper_trading/daily_report.md
```

實務上至少需連續穩定 20 個交易日後，才應考慮使用實盤輔助模式。

## 實盤輔助與人工下單清單

使用本地盤中 CSV：

```bash
python -m src.cli intraday-scan --stock-id 2330 --date 2026-06-18 --time 10:00:00
```

使用明確標記的 demo 盤中資料：

```bash
python -m src.cli intraday-scan --mock --stock-id 2330 --date 2026-06-18 --time 10:00:00
```

輸出：

```text
reports/intraday/manual_order_ticket.csv
reports/intraday/manual_order_ticket.md
reports/intraday/signal_report.md
```

`manual_order_ticket.*` 只是人工檢查清單，不會登入券商、不會控制 APP、不會送出委託。

## 本地 UI

啟動：

```bash
python -m src.cli ui --host 127.0.0.1 --port 8765
```

頁面：

```text
http://127.0.0.1:8765/strategy
http://127.0.0.1:8765/benchmark
```

策略輸出客戶端會顯示策略訊號、風控結果、建議價格、停損停利、建議數量與人工票據輸出路徑。它只會寫入 `reports/intraday/manual_order_ticket.csv` 與 `.md`，不會連接券商。

Benchmark UI 可選擇日資料 CSV、日期區間、起始資金、交易單位與輸出 label，並顯示收益率、最大回撤、交易明細與權益曲線。

## 風控規則

主要設定位於：

```text
config/risk.yaml
config/strategy.yaml
config/universe.yaml
```

第一版風控包含：

- 單一股票最大部位
- 單日最大交易金額
- 單日最大虧損
- 單筆最大虧損
- 單日最大交易次數
- 連續虧損 kill switch
- 最低 20 日平均成交金額
- 開盤避開窗口
- 收盤避開窗口
- stale/missing data 阻擋
- manual confirmation required

策略訊號若未通過成本與風控檢查，不會被輸出到人工下單票據。

## 中信亮點人工操作流程

系統只能產生檢查清單。使用者需自行：

1. 確認標的可交易。
2. 確認標的流動性。
3. 確認目前價格與建議價格差距。
4. 確認單筆風險。
5. 確認今日累積交易次數。
6. 確認今日累積損益。
7. 確認是否接近收盤。
8. 自行開啟中信亮點 APP。
9. 自行輸入委託。
10. 自行確認送出。

## 報告

建立報告模板：

```bash
python -m src.cli build-report
```

主要報告：

```text
reports/daily/market_summary.md
reports/intraday/signal_report.md
reports/paper_trading/performance.md
```

## 免責聲明

本專案是研究與交易流程輔助工具，不是投資建議系統，不保證獲利。所有策略都可能失效，所有資料都可能延遲或錯誤。任何交易決策與下單行為均由使用者自行負責。
