import React, { useState } from 'react';
import ValueDisplay from './ValueDisplay.jsx';
import { formatNum, sumPL } from '../utils.js';

export default function TraderRow({ trader }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('pos');

  const volume = trader.total_buy_qty + trader.total_sell_qty;
  const plClass = trader.gross_pl >= 0 ? 'val-pos' : 'val-neg';
  const symbols = trader.symbols.slice(0, 3).join(', ') + (trader.symbols.length > 3 ? '...' : '');

  const netPosClass = trader.net_position > 0 ? 'badge-long' : trader.net_position < 0 ? 'badge-short' : 'badge-flat';
  const netPosPrefix = trader.net_position > 0 ? '+' : '';

  return (
    <div className={`trader-row ${trader.is_master ? 'master' : ''} ${isOpen ? 'open' : ''}`} style={{ borderRadius: 0, borderTop: 'none' }}>
      <div className="row-header" onClick={() => setIsOpen(!isOpen)}>
        <div className="acc-id">
          <div>
            {trader.account}
            {trader.is_master && <span className="master-tag">MASTER</span>}
          </div>
          {trader.name && (
            <div style={{ fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-muted)', marginTop: '2px' }}>
              {trader.name}
            </div>
          )}
        </div>
        
        <div className="cell-value">
          <span className={`badge ${netPosClass}`}>
            <ValueDisplay value={trader.net_position} text={`${netPosPrefix}${trader.net_position}`} />
          </span>
        </div>
        
        <ValueDisplay className="cell-value" value={volume} text={volume.toLocaleString()} />
        <ValueDisplay className="cell-value val-buy" value={trader.buy_value} text={`$${formatNum(trader.buy_value)}`} />
        <ValueDisplay className="cell-value val-sell" value={trader.sell_value} text={`$${formatNum(trader.sell_value)}`} />
        
        <div className="cell-value" style={{ fontSize: '0.8rem' }}>
          B: {trader.avg_buy.toFixed(4)} <br/> 
          S: {trader.avg_sell.toFixed(4)}
        </div>
        
        <ValueDisplay className={`cell-value ${plClass}`} value={trader.gross_pl} text={`$${formatNum(trader.gross_pl)}`} />
        
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', paddingLeft: '1rem' }}>
          {symbols}
        </div>
        
        <div className="expand-icon">▼</div>
      </div>

      <div className="row-detail">
        <div className="detail-content">
          <div className="tabs">
            <div className={`tab-item ${activeTab === 'pos' ? 'active' : ''}`} onClick={() => setActiveTab('pos')}>
              OPEN POSITIONS ({trader.positions.length})
            </div>
            <div className={`tab-item ${activeTab === 'trades' ? 'active' : ''}`} onClick={() => setActiveTab('trades')}>
              EXECUTION LOG ({trader.trades.length})
            </div>
          </div>
          
          <div className="tab-panel" style={{ display: activeTab === 'pos' ? 'block' : 'none' }}>
            <PositionsTable positions={trader.positions} />
          </div>
          <div className="tab-panel" style={{ display: activeTab === 'trades' ? 'block' : 'none' }}>
            <TradesTable trades={trader.trades} />
          </div>
        </div>
      </div>
    </div>
  );
}

function PositionsTable({ positions }) {
  if (!positions.length) return <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No open positions found.</div>;
  
  const totalPL = sumPL(positions);
  
  return (
    <table className="pro-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Month</th>
          <th>Side</th>
          <th>Quantity</th>
          <th>Entry Price</th>
          <th>Closing Price</th>
          <th>MTM (P&L)</th>
        </tr>
      </thead>
      <tbody>
        {positions.map((p, i) => (
          <tr key={i}>
            <td><strong>{p.Symbol}</strong></td>
            <td>{p.Month}</td>
            <td className={p.Side === 'B' ? 'val-buy' : 'val-sell'}><strong>{p.Side === 'B' ? 'BUY' : 'SELL'}</strong></td>
            <td>{p.Qty}</td>
            <td>{p.AvgPrice.toFixed(4)}</td>
            <td>{p.ClosingPrice.toFixed(4)}</td>
            <td className={p.MTM >= 0 ? 'val-pos' : 'val-neg'}>
              <strong>$<ValueDisplay value={p.MTM} text={formatNum(p.MTM)} /></strong>
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr style={{ background: '#f8fafc', fontWeight: 700 }}>
          <td colSpan="6" style={{ textAlign: 'right' }}>TOTAL GROSS P&L:</td>
          <td className={totalPL >= 0 ? 'val-pos' : 'val-neg'}>${formatNum(totalPL)}</td>
        </tr>
      </tfoot>
    </table>
  );
}

function TradesTable({ trades }) {
  if (!trades.length) return <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No executions recorded for this session.</div>;
  
  return (
    <table className="pro-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Symbol</th>
          <th>Side</th>
          <th>Quantity</th>
          <th>Price</th>
          <th>Trade Value</th>
          <th>Exchange</th>
        </tr>
      </thead>
      <tbody>
        {trades.slice(0, 50).map((t, i) => (
          <tr key={i}>
            <td style={{ color: 'var(--text-muted)' }}>{t.Time}</td>
            <td><strong>{t.Symbol}</strong></td>
            <td className={t.Side === 'B' ? 'val-buy' : 'val-sell'}>{t.Side === 'B' ? 'BUY' : 'SELL'}</td>
            <td>{t.Qty.toLocaleString()}</td>
            <td>{t.Price.toFixed(4)}</td>
            <td>${formatNum(t.Qty * t.Price)}</td>
            <td>{t.Exchange}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
