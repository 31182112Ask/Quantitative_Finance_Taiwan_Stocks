# One-shot implementation task

Repository: `31182112Ask/Quantitative_Finance_Taiwan_Stocks`
Branch: `feat/v2-trading-workstation`
Draft PR: `#1`

Read the root `AGENTS.md` completely. Inspect all current V2 files and complete the largest coherent end-to-end V2 implementation possible in one task. Do not stop at planning, scaffolding or TODOs. Run the project, implement, test, diagnose and repair.

Required sequence:

1. Run existing backend and frontend checks and fix current failures.
2. Introduce clear domain events, adapters and services while preserving startup.
3. Add normalized trade, order-book, connection and session events.
4. Add deterministic multi-timeframe bars: 1s, 5s, 15s, 1m and 5m.
5. Add CSV/Parquet historical replay with virtual clock, pause, step and speed controls.
6. Route strategy intents through risk checks, order state, fills and portfolio accounting.
7. Add stale-data, disconnect, session, loss, position and kill-switch controls.
8. Add local persistence and restart recovery for decisions, orders, fills and account state.
9. Change WebSocket delivery to initial snapshot plus versioned incremental events.
10. Update React to use a typed event reducer and incremental Lightweight Charts updates.
11. Add replay controls, timeframe selection, rule checks, order book, orders, fills, position, PnL, fees, slippage, equity, drawdown and health panels.
12. Isolate the synthetic feed behind an explicit adapter and keep it clearly labeled.
13. Add a `.NET 8` Unified Securities gateway skeleton with documented contracts and explicit stub mode. Do not include proprietary SDK files.
14. Add configuration examples, ignored local state, Windows setup improvements and CI.
15. Add backend, frontend and end-to-end tests where the environment permits.
16. Update `v2/README.md` so it describes only verified behavior.
17. Run every applicable quality gate in `AGENTS.md`, repair failures, inspect the final diff and update Draft PR #1 with factual results.

Constraints:

- Keep V1 intact.
- Keep LIVE disabled unless the official external integration is actually available and validated.
- Never present synthetic data as real market data.
- Never commit secrets or proprietary SDK binaries.
- Do not add unnecessary distributed infrastructure.
- Do not claim strategy profitability.
- Do not merge the Draft PR.

Final response must contain summary, architecture changes, user-visible features, files changed, exact commands and test results, unavailable external dependencies, known limitations and the highest-priority next task.
