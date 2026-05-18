import React from 'react';
import ValueDisplay from './ValueDisplay.jsx';
import { formatNum } from '../utils.js';

export default function GlobalSummary({ data }) {
  const totalPL = data.reduce((s, t) => s + t.gross_pl, 0);
  const totalBuyVal = data.reduce((s, t) => s + t.buy_value, 0);
  const totalSellVal = data.reduce((s, t) => s + t.sell_value, 0);
  const totalTrades = data.reduce((s, t) => s + t.num_trades, 0);

  return (
    <div className="summary-grid">
      <div className="summary-card">
        <div className="summary-label">Aggregate Gross P&L (MTM)</div>
        <ValueDisplay 
          value={totalPL} 
          text={`$${formatNum(totalPL)}`} 
          className={`summary-value ${totalPL >= 0 ? 'val-pos' : 'val-neg'}`} 
        />
      </div>
      <div className="summary-card">
        <div className="summary-label">Total Purchase Value</div>
        <ValueDisplay 
          value={totalBuyVal} 
          text={`$${formatNum(totalBuyVal)}`} 
          className="summary-value" 
        />
      </div>
      <div className="summary-card">
        <div className="summary-label">Total Realization Value</div>
        <ValueDisplay 
          value={totalSellVal} 
          text={`$${formatNum(totalSellVal)}`} 
          className="summary-value" 
        />
      </div>
      <div className="summary-card">
        <div className="summary-label">Total Executions</div>
        <ValueDisplay 
          value={totalTrades} 
          text={totalTrades.toLocaleString()} 
          className="summary-value" 
        />
      </div>
    </div>
  );
}
