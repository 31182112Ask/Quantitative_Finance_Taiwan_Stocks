# AGENTS.md

## 專案名稱

`tw_quant_intraday`

本專案是一個針對台股短期交易與日內交易的本地量化研究與交易輔助系統。系統目標不是直接自動下單，而是建立一套可回測、可監控、可風控、可輸出交易建議的本地工具，最後由使用者透過中信亮點 APP 人工確認下單。

## 核心原則

1. 本專案不得實作券商 APP 自動點擊、螢幕操作、自動登入、自動繞過驗證碼、自動提交委託單等功能。
2. 本專案不得假設中信亮點有公開台股程式交易 API。
3. 本專案的執行層只允許輸出交易建議、委託清單、風控警示與操作提示。
4. 所有交易訊號必須經過風控模組檢查後才能輸出。
5. 所有策略必須先支援回測與紙上交易，不允許直接進入實盤建議。
6. 所有資料、訊號、參數、交易建議、錯誤與例外都必須記錄到本地檔案。
7. 系統必須使用 Asia/Taipei 時區。
8. 系統必須預設使用保守參數，避免過度交易。
9. 系統必須明確區分「研究模式」、「紙上交易模式」、「實盤輔助模式」。
10. 本專案不是投資建議系統，不保證獲利。

## 交易定位

本專案聚焦以下交易型態：

1. 短期波段交易：持有 1 至 10 個交易日。
2. 日內交易：同一交易日內產生買進與賣出建議。
3. 現股當沖輔助：只針對可當沖標的輸出訊號，不自動下單。
4. 不支援高頻交易。
5. 不支援毫秒級撮合。
6. 不支援融資融券、期貨、選擇權與槓桿交易，除非使用者未來明確新增需求。

## 不做的事情

Codex 不得建立以下功能：

1. 自動操作中信亮點 APP 或網頁。
2. 自動提交買賣委託。
3. 自動讀取簡訊、OTP、憑證或帳戶密碼。
4. 儲存任何券商帳號密碼。
5. 使用非官方或違反服務條款的方式抓取券商資料。
6. 建立無風控的交易機器人。
7. 建立以「保證獲利」為目標的策略。
8. 產生未經回測的實盤交易建議。
9. 使用未標記資料來源的價格資料。
10. 在沒有交易成本、滑價與延遲假設的情況下宣稱策略有效。

## 專案目錄結構

請建立以下目錄結構：

```text
tw_quant_intraday/
  AGENTS.md
  README.md
  requirements.txt
  .env.example
  config/
    universe.yaml
    risk.yaml
    strategy.yaml
  data/
    raw/
    processed/
    intraday/
    daily/
  logs/
  reports/
    daily/
    intraday/
    paper_trading/
  notebooks/
  src/
    __init__.py
    config.py
    calendar_tw.py
    data_sources/
      __init__.py
      twse_daily.py
      tpex_daily.py
      finmind_client.py
      intraday_quote.py
      data_cache.py
    market/
      __init__.py
      universe.py
      trading_rules.py
      cost_model.py
      liquidity.py
    features/
      __init__.py
      technical.py
      volume_price.py
      volatility.py
      order_flow_proxy.py
    strategies/
      __init__.py
      base.py
      intraday_momentum.py
      opening_range_breakout.py
      vwap_reversion.py
      t_plus_one_swing.py
    backtest/
      __init__.py
      event_backtester.py
      vector_backtester.py
      metrics.py
      slippage.py
    risk/
      __init__.py
      risk_manager.py
      position_sizing.py
      kill_switch.py
    execution/
      __init__.py
      signal_exporter.py
      manual_order_ticket.py
      broker_checklist.py
    paper/
      __init__.py
      paper_account.py
      paper_engine.py
    reports/
      __init__.py
      report_builder.py
      dashboard_data.py
  tests/
    test_cost_model.py
    test_risk_manager.py
    test_position_sizing.py
    test_backtest_metrics.py
```

## 技術棧

使用 Python 3.11 或以上版本。

必要套件：

```text
pandas
numpy
requests
python-dotenv
pyyaml
matplotlib
pytest
rich
pydantic
```

可選套件：

```text
FinMind
polars
duckdb
plotly
streamlit
```

第一版不要引入複雜深度學習框架。

## 資料來源規範

第一版資料來源優先順序：

1. TWSE 官方公開資料。
2. TPEx 官方公開資料。
3. FinMind。
4. 本地 CSV 快取。

所有資料模組都必須支援：

1. 下載資料。
2. 儲存原始資料。
3. 轉換為標準欄位。
4. 本地快取。
5. 缺漏值檢查。
6. 異常價格檢查。
7. 資料時間戳記錄。

標準日資料欄位：

```text
date
stock_id
stock_name
open
high
low
close
volume
turnover
source
updated_at
```

標準盤中資料欄位：

```text
datetime
stock_id
price
volume
bid_price
ask_price
bid_volume
ask_volume
source
updated_at
```

若無法取得穩定盤中資料，系統必須降級為日資料策略或手動匯入資料，不得偽造即時資料。

## 交易成本模型

必須建立 `src/market/cost_model.py`。

成本模型至少包含：

1. 買進手續費。
2. 賣出手續費。
3. 證券交易稅。
4. 當沖證交稅。
5. 手續費最低收費。
6. 滑價。
7. 買賣價差。
8. 延遲成本。

預設參數放在 `config/risk.yaml` 或 `config/strategy.yaml`。

範例：

```yaml
cost:
  commission_rate: 0.001425
  commission_discount: 0.6
  commission_min: 20
  stock_transaction_tax: 0.003
  day_trade_transaction_tax: 0.0015
  default_slippage_bps: 5
  min_expected_edge_bps: 30
```

策略輸出的預期報酬必須大於交易成本、滑價與安全邊際，否則不得輸出買入訊號。

## 風控規範

必須建立 `src/risk/risk_manager.py`。

所有策略訊號必須通過以下風控：

1. 單一標的最大部位。
2. 單日最大交易金額。
3. 單日最大虧損。
4. 單筆最大虧損。
5. 單日最大交易次數。
6. 連續虧損停止交易。
7. 流動性不足不得交易。
8. 漲跌停附近不得追單。
9. 開盤前 5 分鐘不追價。
10. 收盤前 10 分鐘不新增高風險部位。
11. 當資料延遲或缺漏時停止輸出實盤建議。
12. 當系統錯誤時停止輸出實盤建議。

預設風控參數：

```yaml
risk:
  max_position_pct_per_stock: 0.10
  max_daily_turnover_pct: 0.30
  max_daily_loss_pct: 0.02
  max_trade_loss_pct: 0.008
  max_trades_per_day: 6
  max_consecutive_losses: 3
  min_avg_turnover_20d: 50000000
  avoid_open_minutes: 5
  avoid_close_minutes: 10
  require_manual_confirm: true
```

## 策略模組規範

所有策略必須繼承 `StrategyBase`。

策略輸入：

```text
market_data
features
positions
risk_state
current_time
```

策略輸出：

```text
stock_id
side
signal_type
confidence
entry_price
stop_loss
take_profit
max_position_value
reason
invalid_reason
created_at
```

`side` 只能是：

```text
BUY
SELL
HOLD
CLOSE
```

`signal_type` 只能是：

```text
INTRADAY_MOMENTUM
OPENING_RANGE_BREAKOUT
VWAP_REVERSION
T_PLUS_ONE_SWING
RISK_EXIT
```

## 第一版策略

第一版請實作四個策略。

### 1. Opening Range Breakout

邏輯：

1. 使用開盤後前 15 分鐘高低點作為區間。
2. 價格突破區間高點且成交量放大時產生買入訊號。
3. 跌破區間低點或觸發停損時產生出場訊號。
4. 不在開盤前 15 分鐘內輸出買入訊號。
5. 不在收盤前 10 分鐘新增買入訊號。

### 2. Intraday Momentum

邏輯：

1. 價格高於 VWAP。
2. 5 分鐘報酬率為正。
3. 20 分鐘成交量高於過去均值。
4. 大盤或類股沒有明顯轉弱。
5. 通過成本模型後輸出買入訊號。

### 3. VWAP Reversion

邏輯：

1. 價格短線偏離 VWAP 過大。
2. 成交量未持續放大。
3. 價格開始回到 VWAP。
4. 僅針對高流動性標的。
5. 停損必須緊。

### 4. T+1 Swing

邏輯：

1. 使用日資料。
2. 價格高於 20 日均線與 60 日均線。
3. 近 5 日量價結構轉強。
4. 隔日或數日內出場。
5. 適合無法穩定取得盤中資料時使用。

## 回測規範

必須建立回測模組，並至少輸出以下指標：

```text
total_return
cagr
max_drawdown
sharpe
sortino
win_rate
profit_factor
avg_win
avg_loss
max_consecutive_losses
turnover
trade_count
avg_holding_minutes
cost_total
slippage_total
```

所有回測必須至少包含：

1. 交易成本。
2. 滑價假設。
3. 不可成交假設。
4. 停損停利。
5. 部位限制。
6. 資料延遲檢查。
7. 樣本外測試。

若策略在扣除成本後無正期望，不得輸出為實盤候選策略。

## 紙上交易規範

必須建立 `paper_trading` 模式。

紙上交易要求：

1. 不連接券商。
2. 不下單。
3. 使用本地虛擬帳戶。
4. 記錄每筆模擬交易。
5. 每日產生績效報告。
6. 至少連續 20 個交易日穩定後，才允許進入實盤輔助模式。

紙上交易輸出：

```text
reports/paper_trading/trades.csv
reports/paper_trading/equity_curve.csv
reports/paper_trading/daily_report.md
```

## 執行層規範

本專案的執行層只負責產生人工下單用資訊。

必須建立：

```text
src/execution/signal_exporter.py
src/execution/manual_order_ticket.py
src/execution/broker_checklist.py
```

人工下單票據格式：

```text
date
time
mode
stock_id
stock_name
side
suggested_price
max_price
stop_loss
take_profit
suggested_quantity
suggested_amount
strategy
reason
risk_notes
manual_confirm_required
```

輸出檔案：

```text
reports/intraday/manual_order_ticket.csv
reports/intraday/manual_order_ticket.md
```

不得直接下單。

## 中信亮點人工操作流程

系統只輸出以下檢查清單：

1. 確認標的是否可交易。
2. 確認標的是否可當沖。
3. 確認目前價格與建議價格差距。
4. 確認單筆風險。
5. 確認今日累計交易次數。
6. 確認今日累計損益。
7. 確認是否接近收盤。
8. 使用者自行開啟中信亮點。
9. 使用者自行輸入委託。
10. 使用者自行確認送出。

系統不得操作 APP。

## 報告規範

每日產生三份報告：

```text
reports/daily/market_summary.md
reports/intraday/signal_report.md
reports/paper_trading/performance.md
```

報告內容至少包含：

1. 今日市場狀態。
2. 可交易標的數量。
3. 策略訊號數量。
4. 被風控擋下的訊號。
5. 今日建議交易。
6. 今日不建議交易原因。
7. 風控狀態。
8. 紙上交易績效。
9. 下一交易日注意事項。

## 測試規範

必須使用 pytest。

至少建立以下測試：

1. 成本模型測試。
2. 風控測試。
3. 部位大小測試。
4. 停損停利測試。
5. 回測績效指標測試。
6. 訊號格式測試。
7. 無資料時不得輸出交易建議測試。
8. 超過風控限制時不得輸出交易建議測試。

執行：

```bash
pytest
```

## 命令列介面

建立 CLI：

```bash
python -m src.cli fetch-daily
python -m src.cli build-universe
python -m src.cli backtest --strategy opening_range_breakout
python -m src.cli paper-run
python -m src.cli intraday-scan
python -m src.cli build-report
```

若尚未建立 `src/cli.py`，請建立。

## README 要求

README 必須包含：

1. 專案目標。
2. 不自動下單聲明。
3. 安裝方式。
4. 資料來源設定。
5. 回測方式。
6. 紙上交易方式。
7. 實盤輔助方式。
8. 風控規則。
9. 中信亮點人工操作流程。
10. 免責聲明。

## 開發順序

Codex 請依以下順序建立：

1. 專案骨架。
2. config 模組。
3. 成本模型。
4. 風控模型。
5. 資料下載與快取。
6. 技術指標。
7. 策略基類。
8. 第一版策略。
9. 回測模組。
10. 紙上交易模組。
11. 人工下單票據輸出。
12. 報告模組。
13. CLI。
14. 測試。
15. README。

## 完成標準

第一版完成時必須能做到：

1. 成功下載或讀取台股日資料。
2. 建立可交易標的池。
3. 完成至少一個短期策略回測。
4. 成本模型可計算交易成本。
5. 風控模型可阻擋高風險交易。
6. 紙上交易可執行。
7. 可產生人工下單票據。
8. 所有核心測試通過。
9. README 可讓使用者照步驟執行。
10. 無任何自動下單功能。
