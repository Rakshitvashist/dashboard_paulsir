import React, { useMemo } from 'react';

export default function SymbolSummary({ data }) {
  const symMap = useMemo(() => {
    const map = {};
    data.forEach(trader => {
      trader.trades.forEach(t => {
        if (!t.Symbol || t.Symbol.includes('-')) return;
        if (!map[t.Symbol]) map[t.Symbol] = { buy: 0, sell: 0 };
        if (t.Side === 'B') map[t.Symbol].buy += t.Qty;
        else if (t.Side === 'S') map[t.Symbol].sell += t.Qty;
      });
    });
    return map;
  }, [data]);

  const symbols = Object.keys(symMap).sort();

  return (
    <div className="symbol-summary">
      <div className="summary-label" style={{ marginBottom: '1rem' }}>Contract Wise Volume</div>
      <div className="symbol-grid">
        {symbols.length === 0 ? (
          <div style={{ color: 'var(--text-muted)' }}>No trade data available.</div>
        ) : (
          symbols.map(sym => {
            const net = symMap[sym].buy - symMap[sym].sell;
            return (
              <div className="symbol-card" key={sym}>
                <div className="symbol-card-title">{sym}</div>
                <div className="symbol-stats">
                  <div className="stat-group">
                    <span className="stat-label">Buy Qty</span>
                    <span className="stat-value val-buy">{symMap[sym].buy.toLocaleString()}</span>
                  </div>
                  <div className="stat-group">
                    <span className="stat-label">Sell Qty</span>
                    <span className="stat-value val-sell">{symMap[sym].sell.toLocaleString()}</span>
                  </div>
                  <div className="stat-group">
                    <span className="stat-label">Net Qty</span>
                    <span className={`stat-value ${net >= 0 ? 'val-pos' : 'val-neg'}`}>
                      {net}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
