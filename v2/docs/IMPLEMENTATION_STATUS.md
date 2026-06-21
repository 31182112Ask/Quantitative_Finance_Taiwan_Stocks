# V2 implementation status

## Active branch

`feat/v2-trading-workstation`

## Agent instructions

- Repository rules: `/AGENTS.md`
- Single-task brief: `/CODEX_ONE_SHOT.md`
- Review target: Draft PR #1

## Verified foundation

- React/TypeScript workstation source exists.
- Lightweight Charts integration exists.
- FastAPI WebSocket source exists.
- Tick-to-one-second bar aggregation exists.
- Demonstration EMA/VWAP strategy exists.
- Paper account and cost accounting exist.
- LIVE remains disabled.

## Required agent behavior

The next coding-agent task must first run the current code and tests, then implement and verify the remaining vertical slices described by `AGENTS.md`. It must not report planned or stubbed functionality as complete.

## External boundaries

Real market-data subscriptions, the official Unified Securities SDK, certificates and account credentials are intentionally absent from the repository. The application must use explicit adapters and fail closed when these are unavailable.
