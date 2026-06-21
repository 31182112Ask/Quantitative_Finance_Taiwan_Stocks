import type { ReactNode } from 'react';
import {
  Activity,
  BarChart3,
  CircleDollarSign,
  Crosshair,
  LockKeyhole,
  Radio,
  ShieldAlert,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { MarketChart } from './components/MarketChart';
import { useMarketStream } from './hooks/useMarketStream';
import type { DecisionAction } from './types';

const money = new Intl.NumberFormat('zh-TW', {
  style: 'currency',
  currency: 'TWD',
  maximumFractionDigits: 0,
});
const number = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 2 });

export default function App() {
  const { snapshot, status } = useMarketStream();

  if (!snapshot) {
    return (
      <main className="loading-screen">
        <Activity className="spin" size={22} />
        <span>正在连接本地行情引擎</span>
        <small>{status}</small>
      </main>
    );
  }

  const decision = snapshot.decision;
  const account = snapshot.account;
  const totalPnl = account.realized_pnl + account.unrealized_pnl;
  const pnlClass = totalPnl >= 0 ? 'positive' : 'negative';
  const actionClass = actionToClass(decision?.action ?? 'HOLD');

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <BarChart3 size={20} />
          <strong>QFT Workstation</strong>
        </div>
        <div className="symbol-block">
          <strong>{snapshot.symbol}</strong>
          <span>國泰臺灣加權正2</span>
        </div>
        <div className="quote-block">
          <strong>{snapshot.last_price?.toFixed(2) ?? '--'}</strong>
          <span className={snapshot.change_pct >= 0 ? 'positive' : 'negative'}>
            {snapshot.change_pct >= 0 ? '+' : ''}{snapshot.change_pct.toFixed(2)}%
          </span>
        </div>
        <nav className="mode-switch" aria-label="运行模式">
          <button disabled>BACKTEST</button>
          <button className="active">PAPER</button>
          <button disabled title="尚未配置统一证券 API">
            <LockKeyhole size={13} /> LIVE
          </button>
        </nav>
        <div className="connection-state">
          {status === 'OPEN' ? <Wifi size={15} /> : <WifiOff size={15} />}
          <span>{snapshot.feed}</span>
          <b>{status}</b>
        </div>
      </header>

      <aside className="tool-rail" aria-label="图表工具">
        <button title="十字线"><Crosshair size={18} /></button>
        <button title="指标"><Activity size={18} /></button>
        <button title="风险"><ShieldAlert size={18} /></button>
        <button title="行情"><Radio size={18} /></button>
      </aside>

      <section className="workspace">
        <section className="chart-panel panel">
          <div className="panel-header">
            <div>
              <strong>{snapshot.symbol} · 1秒</strong>
              <span>O/H/L/C 由逐笔成交聚合</span>
            </div>
            <div className="legend">
              <span><i className="legend-dot vwap" />VWAP</span>
              <span><i className="legend-dot entry" />决策线</span>
              <span><i className="legend-dot stop" />止损</span>
              <span><i className="legend-dot target" />止盈</span>
            </div>
          </div>
          <div className="chart-wrap">
            <MarketChart snapshot={snapshot} />
          </div>
        </section>

        <aside className="decision-panel panel">
          <div className="panel-header compact">
            <strong>策略决策</strong>
            <span className={`action-badge ${actionClass}`}>{decision?.action ?? 'WAIT'}</span>
          </div>
          <div className="score-card">
            <div>
              <span>决策评分</span>
              <strong>{decision?.score ?? 0}</strong>
            </div>
            <div className="score-track">
              <i style={{ width: `${decision?.score ?? 0}%` }} />
            </div>
          </div>
          <p className="decision-reason">{decision?.reason ?? '等待足够行情数据'}</p>
          <dl className="metric-list">
            <Metric label="EMA 9" value={decision?.fast_ema} />
            <Metric label="EMA 21" value={decision?.slow_ema} />
            <Metric label="VWAP" value={decision?.vwap} />
          </dl>
          <div className="risk-box">
            <div><span>计划进场</span><strong>{formatPrice(decision?.entry)}</strong></div>
            <div className="negative"><span>风险止损</span><strong>{formatPrice(decision?.stop)}</strong></div>
            <div className="positive"><span>目标止盈</span><strong>{formatPrice(decision?.take_profit)}</strong></div>
          </div>
          <div className="execution-lock">
            <LockKeyhole size={16} />
            <div>
              <strong>实盘硬锁定</strong>
              <span>统一证券执行器尚未接入，任何信号均只进入 Paper Broker。</span>
            </div>
          </div>
        </aside>

        <section className="bottom-grid">
          <StatCard icon={<CircleDollarSign size={18} />} label="总损益" value={money.format(totalPnl)} className={pnlClass} />
          <StatCard label="已实现" value={money.format(account.realized_pnl)} />
          <StatCard label="未实现" value={money.format(account.unrealized_pnl)} />
          <StatCard label="持仓" value={`${account.position_qty.toLocaleString()} 股`} />
          <StatCard label="成交均价" value={account.avg_price ? account.avg_price.toFixed(2) : '--'} />
          <StatCard label="成本/税费" value={money.format(account.fees)} />
          <StatCard label="最大回撤" value={`${(account.max_drawdown * 100).toFixed(3)}%`} className="negative" />
          <StatCard label="成交次数" value={String(account.trades)} />
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value?: number }) {
  return <div><dt>{label}</dt><dd>{value == null ? '--' : number.format(value)}</dd></div>;
}

function StatCard({
  icon,
  label,
  value,
  className = '',
}: {
  icon?: ReactNode;
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <article className="stat-card">
      <span>{icon}{label}</span>
      <strong className={className}>{value}</strong>
    </article>
  );
}

function formatPrice(value: number | null | undefined) {
  return value == null ? '--' : value.toFixed(2);
}

function actionToClass(action: DecisionAction) {
  if (action === 'BUY') return 'buy';
  if (action === 'SELL') return 'sell';
  return 'hold';
}
