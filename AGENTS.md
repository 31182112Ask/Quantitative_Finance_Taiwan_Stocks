# AGENTS.md

## 1. Mission

This repository is developing a Windows-first quantitative trading workstation for the Taiwan-listed leveraged ETF `00663L` (Cathay Taiwan Weighted 2X).

The active implementation is V2 under `v2/`. Its target is one application with one UI and one event model for:

- historical replay and backtesting;
- real-time paper trading using real market data;
- future live execution through an official Unified Securities integration;
- high-refresh TradingView-style visualization;
- deterministic strategy, risk, order, fill, position and PnL state.

The old manual-only CTBC design is obsolete. Do not restore it. Do not create a second unrelated application beside V2.

## 2. Agent operating mode

Work as an autonomous senior software engineer. The requested task is intended to be completed in one Codex/GPT-5.5 conversation whenever technically possible.

Rules:

1. Read this entire file before editing.
2. Inspect the repository, current branch, existing tests and current V2 implementation before planning changes.
3. Do not ask questions that can be resolved from the repository or by choosing a safe, conventional default.
4. Make a best-effort end-to-end implementation instead of stopping after scaffolding.
5. Do not spend the task only writing plans, TODO files, interfaces or mock screenshots.
6. Implement working vertical slices, run them, test them and repair failures.
7. Use small cohesive modules. Do not place the whole system in one file.
8. Preserve existing working behavior unless the replacement is demonstrably better.
9. Keep V1 intact unless the task explicitly asks to delete it.
10. Work on the current feature branch. Do not merge into `main`.
11. Do not commit secrets, credentials, certificates, account identifiers or real trading tokens.
12. At the end, report files changed, commands run, test results, remaining external blockers and exact next steps.

When an external service, proprietary SDK or credential is unavailable:

- define a typed adapter;
- implement a deterministic local adapter or replay adapter;
- document the missing configuration;
- keep live behavior locked;
- continue completing all work that does not require that external dependency.

Never fake successful connectivity to a market-data vendor, exchange or broker.

## 3. Repository scope

### Protected legacy scope

Existing V1 files outside `v2/` may contain prior research and utilities. Treat them as read-only unless a shared root-level file must be updated.

### Active scope

Primary development belongs in:

```text
v2/
  backend/
  frontend/
  gateway/              # create when implementing the C# broker bridge
  config/               # create for versioned non-secret configuration
  data/                 # schemas and local sample/replay data only
  docs/
  scripts/
  tests/
  README.md
  setup_v2.bat
  start_v2.bat
```

Root-level files that may be edited:

```text
AGENTS.md
CODEX_ONE_SHOT.md
README.md
.gitignore
.github/
```

## 4. Current foundation

The current V2 branch already provides:

- React and TypeScript frontend;
- TradingView Lightweight Charts;
- FastAPI backend;
- WebSocket snapshots;
- deterministic Tick to one-second OHLCV/turnover/VWAP aggregation;
- EMA9/EMA21 and VWAP demonstration strategy;
- chart entry, stop, target and signal markers;
- Paper Broker with fees, ETF sell tax and slippage;
- position, realized/unrealized PnL, fees and drawdown display;
- Windows setup and start scripts;
- a hard-disabled LIVE mode.

Do not replace this with Streamlit, notebooks or a static HTML dashboard. Extend and refactor the existing architecture.

## 5. Product requirements

The finished workstation should support the following modes through the same UI and state contracts.

### BACKTEST

- historical tick or event replay;
- deterministic virtual clock;
- play, pause, single-step and speed controls;
- configurable latency, commission, tax, spread and slippage;
- identical strategy and risk code to paper/live;
- reproducible results for the same input and seed;
- trade list, fill list, equity curve, drawdown and metrics;
- exportable run configuration and results.

### PAPER

- real-time market-data adapter;
- Paper Broker only;
- realistic order lifecycle and fill simulation;
- persistent session state and audit logs;
- continuous comparison between strategy theoretical price and simulated fill;
- no outbound broker order.

### LIVE

- official broker adapter only;
- default disabled;
- two-stage configuration and explicit arming;
- obvious LIVE visual state;
- account, order, fill and position reconciliation;
- kill switch, cancel-all and flatten controls;
- no order submission when data, gateway or reconciliation state is unhealthy.

The UI may share components, but modes must be visually unmistakable.

## 6. Target architecture

Use a deterministic event-driven architecture inspired by mature open-source trading engines without copying their source code.

```text
MarketDataAdapter
  -> Normalizer
  -> EventBus
  -> BarAggregator / OrderBookState / FeatureEngine
  -> StrategyEngine
  -> RiskEngine
  -> OrderManager
  -> ExecutionAdapter (Replay / Paper / Unified)
  -> Portfolio and PnL
  -> Persistence and Audit Log
  -> WebSocket API
  -> React UI
```

Required principles:

- domain logic must not import FastAPI or React concerns;
- adapters depend on domain interfaces, not the reverse;
- backtest, paper and live use the same strategy/risk/order domain models;
- timestamps, sequence numbers and source identity are first-class fields;
- raw events are append-only;
- state transitions are explicit and testable;
- no hidden global mutable state for trading logic;
- use dependency injection or clear construction functions;
- all money and quantity calculations must have an explicit unit.

## 7. Backend conventions

Use Python 3.12 or newer.

Preferred libraries:

- FastAPI and Uvicorn;
- Pydantic v2 for API/config schemas;
- asyncio for I/O;
- Polars or standard Python for event transforms where useful;
- DuckDB and Parquet for local analytical storage;
- SQLite only for small metadata if needed;
- pytest, pytest-asyncio, Ruff and mypy;
- structlog or standard logging with JSON formatting.

Avoid adding a heavy distributed system for a single-instrument workstation. Redis, Kafka and PostgreSQL are not required for the first complete local version unless a measured need exists.

Backend packages should move toward:

```text
v2/backend/app/
  api/
  domain/
    events.py
    market.py
    orders.py
    portfolio.py
    strategy.py
    risk.py
  adapters/
    market_data/
    execution/
    persistence/
  services/
    engine.py
    replay.py
    reconciliation.py
  config.py
  main.py
```

Refactor incrementally. Keep imports working after every change.

## 8. Frontend conventions

Use React, TypeScript and Vite. Continue using TradingView Lightweight Charts.

Requirements:

- strict TypeScript;
- no `any` unless isolated and justified;
- domain/API types centralized;
- WebSocket reconnect with exponential backoff;
- stale-data detection;
- render throttling separated from event processing;
- responsive desktop layout optimized for 1920x1080 and 2560x1440;
- usable at 1366x768;
- do not imitate TradingView branding or proprietary assets;
- use original layout and labels while following professional charting ergonomics.

The UI must eventually include:

1. symbol, mode, market status and clock;
2. data-source, connection and latency indicators;
3. candlestick chart with 1s, 5s, 15s, 1m and 5m views;
4. VWAP and configurable indicators;
5. entry, stop, target, trailing-stop and invalidation lines;
6. signal, order and fill markers that are visually distinct;
7. risk/reward shaded region where technically practical;
8. volume and order-flow panels;
9. five-level order book and spread;
10. strategy rule checklist with current values and thresholds;
11. orders, fills, positions and account panels;
12. realized/unrealized PnL, fees, slippage, equity and drawdown;
13. replay controls in BACKTEST;
14. cancel-all, stop-strategy and flatten controls in LIVE;
15. settings drawer for strategy, risk and cost assumptions.

Do not update the entire chart with full `setData` every 100 ms once an incremental `update` path is available. Use full loading for initialization and incremental updates for real-time events.

## 9. Market-data model

Use exchange time and receive time separately.

Every normalized event must contain as applicable:

```text
schema_version
source
symbol
session
exchange_timestamp_ns
receive_timestamp_ns
sequence
is_snapshot
is_trial
```

Trade event fields:

```text
price
size
aggressor_side
trade_id
```

Order-book fields:

```text
bid_price_1..5
bid_size_1..5
ask_price_1..5
ask_size_1..5
```

Required controls:

- deduplication;
- out-of-order detection;
- sequence-gap detection when the source provides sequence values;
- heartbeat timeout;
- reconnect and resubscribe;
- snapshot plus incremental recovery when supported;
- stale-market flag;
- trial-match and non-trade event filtering;
- cumulative-volume reconciliation;
- raw event persistence before derived aggregation when feasible.

Do not treat REST polling as the primary high-refresh feed. Use WebSocket or the official push API where available.

## 10. Bar aggregation

Bars are derived from normalized trades, not from UI timers.

Support:

- one second;
- five seconds;
- fifteen seconds;
- one minute;
- five minutes.

Each bar should include:

```text
time
open
high
low
close
volume
turnover
trade_count
vwap
buy_volume
sell_volume
```

Requirements:

- deterministic bucket boundaries in `Asia/Taipei`;
- correct handling of missing-trade intervals;
- configurable empty-bar behavior;
- final/provisional bar distinction;
- no mutation of finalized historical bars except through an explicit correction event;
- unit tests for boundaries, gaps, duplicates, out-of-order ticks and session transitions.

## 11. Auxiliary data

The architecture must permit synchronized inputs for:

- `00663L` trades and five-level order book;
- Taiwan Weighted Index;
- near-month Taiwan index futures when a licensed source exists;
- ETF NAV or estimated NAV when a valid source exists;
- market/session status.

Derived features may include:

- spread;
- mid-price;
- microprice;
- depth imbalance;
- trade imbalance;
- volume velocity;
- VWAP distance;
- short-horizon realized volatility;
- index/futures/ETF short-term divergence.

Feature calculations must be pure or state-explicit and unit tested.

## 12. Historical data and replay

Create an adapter capable of reading local CSV and Parquet tick files. Do not require paid data to run tests.

Replay requirements:

- deterministic ordering by exchange timestamp, sequence and receive timestamp;
- virtual clock;
- configurable speed including maximum speed;
- pause and single-step;
- optional injected latency and packet gaps;
- same normalized event types as real-time adapters;
- no look-ahead;
- reproducible random seed for simulated fills.

Include a small synthetic sample dataset generated by code or stored as a tiny fixture. Clearly label it synthetic.

## 13. Strategy framework

The existing EMA/VWAP strategy is a demonstration, not a claim of profitability.

Create a strategy interface with lifecycle methods such as:

```text
on_start
on_market_event
on_bar
on_order_update
on_fill
on_stop
```

Strategy output should be an intent, not a direct broker call.

At minimum implement configurable examples for:

- VWAP plus EMA trend/momentum;
- opening-range breakout;
- VWAP mean reversion or explicitly document why it is unsuitable for a given regime.

Each decision must expose:

```text
strategy_id
intent_id
time
action
score
entry_reference
stop
take_profit
invalidation
quantity_hint
reason_codes
rule_checks
```

No opaque AI-generated BUY/SELL signal is allowed in the execution path. Models may assist research, but production decisions must be inspectable and reproducible.

## 14. Cost and fill model

Centralize Taiwan ETF trading costs in configuration.

Model at least:

- commission rate;
- commission discount;
- minimum commission;
- ETF sell transaction tax;
- spread crossing;
- configurable slippage ticks;
- configurable latency;
- partial fills;
- rejected and expired orders;
- marketable and non-marketable limit orders.

Do not hard-code a claim that one commission discount applies to every user. Defaults must be clearly marked as assumptions.

Paper fills should depend on available market information. When only trades are present, use a conservative documented approximation. When order book data is present, use bid/ask and available size.

## 15. Order and execution state machine

Use explicit enums and validated transitions.

Suggested states:

```text
CREATED
RISK_REJECTED
READY
SUBMITTING
ACKNOWLEDGED
PARTIALLY_FILLED
FILLED
CANCEL_PENDING
CANCELED
REJECTED
EXPIRED
UNKNOWN
```

Required behavior:

- idempotent client order IDs;
- no duplicate submission after timeout without reconciliation;
- partial fill accounting;
- cancel/replace tracking;
- broker and local position reconciliation;
- restart recovery from persisted state;
- unknown-state handling that blocks new risk;
- append-only order/fill audit events.

## 16. Unified Securities gateway

The broker integration is expected to use the official Unified Securities domestic securities API and may require a Windows C# process.

Create a gateway boundary rather than loading proprietary DLLs throughout Python.

Preferred shape:

```text
v2/gateway/UnifiedBrokerGateway/
  .NET 8 service
  broker SDK wrapper
  local authenticated IPC or WebSocket/gRPC endpoint
  health endpoint
  order/update stream
  account/position query
```

Python communicates only with the local gateway contract.

Rules:

- proprietary DLLs and certificates are never committed;
- credentials come from environment variables, Windows credential storage or ignored local config;
- include an `.env.example` or config example with placeholders only;
- gateway startup without SDK must fail clearly or run in explicit stub mode;
- stub mode must be visibly named and cannot claim a live connection;
- LIVE order submission remains disabled until integration tests and manual arming gates pass.

## 17. Risk engine

Risk checks execute before every order and continuously while a position exists.

Implement configurable controls for:

- maximum position quantity and notional;
- maximum order quantity and notional;
- maximum daily loss;
- maximum loss per trade;
- maximum daily trades and turnover;
- maximum consecutive losses;
- stale data;
- disconnected market feed;
- disconnected broker gateway;
- unresolved order state;
- local/broker position mismatch;
- excessive spread;
- abnormal slippage;
- market session restrictions;
- no new position near forced-flat time;
- forced flatten before close;
- global kill switch.

Risk rejections must include stable machine-readable reason codes and user-readable explanations.

## 18. Persistence and audit

Persist enough state to reconstruct what happened.

Minimum records:

- raw normalized market events or replay source references;
- bars and features used by the strategy;
- strategy decisions and rule checks;
- risk decisions;
- orders and transitions;
- fills;
- position and account snapshots;
- connection state changes;
- latency measurements;
- configuration snapshot;
- software version or git commit when available.

Use UTC or explicit timezone-aware timestamps internally and display `Asia/Taipei` in the UI.

Do not log secrets or full credential-bearing payloads.

## 19. API and WebSocket contracts

Version public payloads.

Avoid sending the full 600-bar history on every tick. Use:

- initial snapshot;
- incremental bar update;
- finalized bar event;
- indicator update;
- decision event;
- order/fill event;
- account update;
- health/latency event.

Keep a development snapshot endpoint for diagnostics.

Define shared schemas and add contract tests so frontend and backend fields cannot silently diverge.

## 20. Configuration

Versioned non-secret configuration belongs under `v2/config/`.

Recommended files:

```text
app.example.yaml
strategy.example.yaml
risk.example.yaml
costs.example.yaml
market_data.example.yaml
```

Support environment overrides.

Every run must know:

- mode;
- symbol;
- timezone;
- data adapter;
- execution adapter;
- strategy configuration;
- risk configuration;
- cost/fill assumptions;
- storage path.

Invalid or unsafe live configuration must fail closed.

## 21. Testing requirements

### Backend unit tests

Cover at least:

- trade normalization;
- bar boundaries and gaps;
- indicators and features;
- strategy transitions;
- risk rejection reasons;
- cost calculations;
- order state transitions;
- partial fills;
- PnL and drawdown;
- replay determinism;
- persistence/recovery.

### Backend integration tests

Cover:

- replay to strategy to risk to Paper Broker to portfolio;
- WebSocket initial snapshot and incremental events;
- disconnect/stale-data behavior;
- forced-flat behavior;
- duplicate/out-of-order event handling.

### Frontend tests

Use Vitest and React Testing Library where practical. Cover:

- connection state;
- mode badge and live lock;
- decision/risk display;
- order and position rendering;
- stale-data warning;
- incremental event reducer.

### End-to-end smoke test

Prefer Playwright for one local smoke path:

1. launch backend and frontend;
2. load the workstation;
3. verify demo/replay data appears;
4. verify a chart and key panels render;
5. verify mode and live lock are visible;
6. capture a screenshot artifact when the environment supports it.

Do not require a real broker or paid feed in CI.

## 22. Quality gates

Run all available commands before declaring completion.

Backend:

```powershell
cd v2/backend
python -m compileall app tests
python -m ruff check .
python -m mypy app
python -m pytest -q
```

Frontend:

```powershell
cd v2/frontend
npm ci
npm run build
npm test -- --run
```

If scripts differ after refactoring, update this file and README.

A check that cannot run because the environment lacks network access, Node, a proprietary SDK or credentials must be listed exactly. Do not report it as passed.

## 23. Windows developer experience

Maintain working commands for a new Windows machine.

`setup_v2.bat` should:

- validate Python and Node versions;
- create the virtual environment;
- install backend and frontend dependencies;
- provide actionable error messages;
- be safe to rerun.

`start_v2.bat` should:

- start backend and frontend;
- avoid opening duplicate processes when practical;
- show URLs and log locations;
- fail clearly when setup is incomplete.

Also provide PowerShell equivalents when useful.

## 24. Documentation

Update `v2/README.md` as implementation changes.

It must clearly state:

- what is real and what is synthetic/stubbed;
- supported modes;
- architecture;
- setup and launch instructions;
- test commands;
- data import format;
- market-data adapter configuration;
- broker gateway status;
- risk controls;
- limitations and known issues.

Do not describe planned functionality as already working.

## 25. Security and safety

- Never store passwords, tokens, certificates or account data in git.
- Never bypass broker authentication, OTP, certificate checks or rate limits.
- Never automate a broker web page or desktop UI when an official API is required.
- Never enable LIVE because a boolean was changed in the frontend.
- Live arming must be enforced server-side and gateway-side.
- Bind local services to loopback by default.
- Authenticate local gateway commands if the gateway can place orders.
- Validate every inbound event and command.
- Escape user-visible text and avoid unsafe HTML.
- Pin or constrain dependencies and keep lockfiles.

## 26. Performance targets

For the small initial symbol set, target:

- process each market event immediately;
- normal strategy/risk event path under 5 ms on a typical desktop, measured rather than assumed;
- frontend visual refresh around 50-100 ms;
- chart updates incremental;
- batched persistence that does not block the event loop;
- no unbounded queues or histories;
- visible latency and queue-depth metrics.

This is a low-latency retail workstation, not exchange-colocated HFT. Do not claim microsecond or guaranteed latency.

## 27. One-pass implementation order

For a broad completion task, execute in this order without stopping for approval:

1. inspect and run the current project;
2. fix dependency/build/test failures;
3. introduce domain events and adapter interfaces;
4. implement deterministic historical replay;
5. refactor Paper Broker into an order state machine;
6. add risk engine and session controls;
7. add incremental WebSocket contracts;
8. update the React data store and chart updates;
9. add replay controls, order book, decision, order, fill and PnL panels;
10. add persistence, exports and recovery;
11. create the C# gateway skeleton and Python client contract;
12. keep real broker calls disabled unless the official SDK is actually available;
13. add tests, CI and documentation;
14. run the full validation matrix;
15. repair failures;
16. provide the final implementation report.

Do not stop after step 3 and call the task complete.

## 28. Definition of done

A substantial V2 implementation is complete only when all applicable items below are true:

- one command installs the project on Windows;
- one command launches the local workstation;
- frontend production build succeeds;
- backend type/lint/tests succeed;
- historical replay runs through the same strategy/risk/execution pipeline;
- Paper mode runs with real-time adapter architecture and a deterministic local feed;
- bars update incrementally and multiple timeframes are available;
- strategy decisions, risk state, orders, fills and PnL are visible;
- costs and slippage are included;
- stale data and disconnects stop new orders;
- forced-flat and kill-switch behavior are tested;
- state and audit records persist locally;
- live mode is visibly and technically locked without valid gateway configuration;
- documentation accurately distinguishes complete, stubbed and unavailable features;
- no existing V1 behavior was unintentionally broken.

External market-data subscriptions and broker credentials are not required for local completion, but their adapters and failure-closed boundaries are required.

## 29. Final response format for the coding agent

Return a concise implementation report containing:

```text
Summary
Architecture changes
User-visible features
Files added/changed
Tests and exact results
Commands to run
External integrations still requiring user credentials/SDK
Known limitations
Recommended next task
```

Do not state that the application is production-ready for real-money trading unless live integration, reconciliation, failure testing and controlled acceptance testing have actually been completed.
