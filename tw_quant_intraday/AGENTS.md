# tw_quant_intraday Project Rules

This project is a local Taiwan stock short-term and intraday research assistant.
It must never automate broker login, app clicks, order submission, credential capture,
or any other broker-side action.

Allowed outputs for live-assist workflows are limited to local manual review files:

- `reports/intraday/manual_order_ticket.csv`
- `reports/intraday/manual_order_ticket.md`

The system supports research, backtesting, paper trading, reporting, and manual
order ticket generation only. All signals must pass cost and risk checks before
they can be exported.
