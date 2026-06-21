# V2 — 00663L Trading Workstation

这是独立于 V1 的首个可运行垂直切片。目标是让历史回放、实时模拟和未来实盘共享同一套 UI、行情事件模型、策略接口与账户状态模型。

## 当前已实现

- React + TradingView Lightweight Charts 5.2 风格工作台
- FastAPI WebSocket 实时推送
- 逐笔 Tick → 1 秒 OHLCV / Turnover / VWAP 聚合
- EMA9 / EMA21 + VWAP 透明示例策略
- 进出场标记、进场线、止损线、止盈线
- Paper Broker：滑价、手续费、ETF 卖出交易税、持仓、已实现/未实现损益与最大回撤
- 自动重连与 100ms 图表刷新
- LIVE 模式硬锁定，尚未配置统一证券 API 时不会产生真实委托
- 后端单元测试覆盖 K 线聚合与模拟成交闭环

> 当前行情是明确标记的 `DEMO_TICK_FEED`，用于验证 UI 和事件管线，不是真实 00663L 行情。

## 快速启动（Windows）

首次执行：

```bat
setup_v2.bat
```

之后执行：

```bat
start_v2.bat
```

浏览器打开 `http://127.0.0.1:5173`。

## 手动启动

后端：

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m uvicorn app.main:app --reload
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

## 设计边界

这版只完成可运行骨架，不声称策略有正期望，也没有假装已经接入券商。下一阶段应按以下顺序推进：

1. 抽象 `MarketDataAdapter`，接入真实逐笔成交与五档。
2. 增加历史 Tick 文件回放器，让 BACKTEST 使用同一事件管线。
3. 增加订单状态机、部分成交、撤改单和断线恢复。
4. 建立统一证券 C# Gateway，并在通过模拟验收后才解除 LIVE 锁。
5. 把示例策略替换为正式的 00663L 日冲策略与独立风险引擎。

## 参考的开源设计

- TradingView Lightweight Charts：金融图表、实时更新、Series Markers 与 Price Lines。
- QuantConnect LEAN：事件驱动、模块化数据/策略/券商组件。
- NautilusTrader：确定性事件驱动架构与回测/实盘一致性。
- Freqtrade：Dry-run 与 Live 模式隔离、风险配置和运行状态监控。

本项目只借鉴架构原则和公开 API，不复制第三方项目代码。
