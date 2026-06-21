export type RunMode = 'BACKTEST' | 'PAPER' | 'LIVE';
export type DecisionAction = 'BUY' | 'SELL' | 'HOLD';

export interface Bar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover: number;
  trades: number;
  vwap: number;
}

export interface Decision {
  time: number;
  action: DecisionAction;
  reason: string;
  score: number;
  entry: number | null;
  stop: number | null;
  take_profit: number | null;
  fast_ema: number;
  slow_ema: number;
  vwap: number;
}

export interface SignalMarker {
  time: number;
  action: DecisionAction;
  price: number;
  text: string;
}

export interface AccountState {
  starting_equity: number;
  cash: number;
  position_qty: number;
  avg_price: number;
  realized_pnl: number;
  unrealized_pnl: number;
  fees: number;
  equity: number;
  peak_equity: number;
  max_drawdown: number;
  trades: number;
}

export interface MarketSnapshot {
  type: 'snapshot';
  revision: number;
  symbol: string;
  mode: RunMode;
  feed: string;
  connected: boolean;
  server_time_ms: number;
  last_price: number | null;
  change_pct: number;
  bars: Bar[];
  decision: Decision | null;
  signals: SignalMarker[];
  account: AccountState;
  latency_ms: number;
  live_trading_enabled: boolean;
}
