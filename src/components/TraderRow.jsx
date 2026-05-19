import React, { useState, useMemo } from 'react';
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontWeight: 'bold' }}>{trader.account}</span>
            {trader.backcode && (
              <span style={{
                fontSize: '0.7rem',
                background: 'rgba(255, 255, 255, 0.1)',
                padding: '1px 5px',
                borderRadius: '3px',
                color: 'var(--text-muted)',
                fontWeight: 'normal'
              }}>
                {trader.backcode}
              </span>
            )}
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
  
  const totalPL = positions.reduce((sum, p) => sum + (p.mtm || 0), 0);
  
  return (
    <div style={{ overflowX: 'auto', width: '100%' }}>
      <table className="pro-table" style={{ minWidth: '1350px' }}>
        <thead>
          <tr>
            <th>SCRIP</th>
            <th>EXCHANGE</th>
            <th>Scrip Name</th>
            <th>Expiry Date</th>
            <th>CALLPUT</th>
            <th>STRIKE</th>
            <th>BF QTY</th>
            <th>Buy Qty</th>
            <th>Sell Qty</th>
            <th>Net Qty</th>
            <th>Average Rate</th>
            <th>LTP</th>
            <th>MTM</th>
            <th>IntraDay Mtm</th>
            <th>Exchange Delta</th>
            <th>Day Bought Qty</th>
            <th>Day Sold Qty</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p, i) => {
            const netQtyClass = p.net_qty > 0 ? 'val-buy' : p.net_qty < 0 ? 'val-sell' : '';
            const netQtyText = p.net_qty > 0 ? `+${p.net_qty}` : `${p.net_qty}`;
            
            const bfQtyClass = p.bf_qty > 0 ? 'val-buy' : p.bf_qty < 0 ? 'val-sell' : '';
            const bfQtyText = p.bf_qty > 0 ? `+${p.bf_qty}` : `${p.bf_qty}`;
            
            return (
              <tr key={i}>
                <td><strong>{p.scrip}</strong></td>
                <td>{p.exchange}</td>
                <td>{p.scrip_name}</td>
                <td>{p.expiry_date}</td>
                <td>{p.callput}</td>
                <td>{p.strike}</td>
                <td className={bfQtyClass}>{bfQtyText}</td>
                <td>{p.buy_qty}</td>
                <td>{p.sell_qty}</td>
                <td className={netQtyClass}><strong>{netQtyText}</strong></td>
                <td>{p.average_rate.toFixed(4)}</td>
                <td>{p.ltp.toFixed(4)}</td>
                <td className={p.mtm >= 0 ? 'val-pos' : 'val-neg'}>
                  <strong>$<ValueDisplay value={p.mtm} text={formatNum(p.mtm)} /></strong>
                </td>
                <td className={p.intraday_mtm >= 0 ? 'val-pos' : 'val-neg'}>
                  $<ValueDisplay value={p.intraday_mtm} text={formatNum(p.intraday_mtm)} />
                </td>
                <td>{p.exchange_delta}</td>
                <td>{p.day_bought_qty}</td>
                <td>{p.day_sold_qty}</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr style={{ background: '#f8fafc', fontWeight: 700 }}>
            <td colSpan="12" style={{ textAlign: 'right' }}>TOTAL GROSS P&L:</td>
            <td className={totalPL >= 0 ? 'val-pos' : 'val-neg'}>${formatNum(totalPL)}</td>
            <td colSpan="4"></td>
          </tr>
        </tfoot>
      </table>
    </div>
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
