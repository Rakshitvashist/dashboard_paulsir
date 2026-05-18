import React, { useState, useMemo } from 'react';
import TraderRow from './TraderRow.jsx';

export default function TraderList({ data }) {
  const [search, setSearch] = useState('');
  const [posFilter, setPosFilter] = useState('all');
  const [sortBy, setSortBy] = useState('pl');
  const [sortOrder, setSortOrder] = useState('desc'); // 'desc' (downward) or 'asc' (upward)
  const [pinMaster, setPinMaster] = useState(true); // Pin master to top or sort overall

  const filteredAndSortedData = useMemo(() => {
    let filtered = data;
    const q = search.toLowerCase();

    // Filter
    if (q || posFilter !== 'all') {
      filtered = data.filter(t => {
        let match = true;
        if (q) {
          const accMatch = t.account.toLowerCase().includes(q);
          const symMatch = t.symbols.some(s => s.toLowerCase().includes(q));
          const masterMatch = t.is_master && "master".includes(q);
          if (!accMatch && !symMatch && !masterMatch) match = false;
        }

        if (match && posFilter !== 'all') {
          if (posFilter === 'long' && t.net_position <= 0) match = false;
          else if (posFilter === 'short' && t.net_position >= 0) match = false;
          else if (posFilter === 'flat' && t.net_position !== 0) match = false;
        }
        return match;
      });
    }

    // Sort
    return [...filtered].sort((a, b) => {
      // Pin masters on top if selected
      if (pinMaster) {
        if (a.is_master && !b.is_master) return -1;
        if (!a.is_master && b.is_master) return 1;
      }

      let comparison = 0;
      switch (sortBy) {
        case 'volume':
          comparison = (b.total_buy_qty + b.total_sell_qty) - (a.total_buy_qty + a.total_sell_qty);
          break;
        case 'buy_value':
          comparison = b.buy_value - a.buy_value;
          break;
        case 'trades':
          comparison = b.num_trades - a.num_trades;
          break;
        case 'id':
          comparison = a.account.localeCompare(b.account);
          break;
        case 'pl':
        default:
          comparison = b.gross_pl - a.gross_pl;
          break;
      }

      // Handle Ascending vs Descending (upward vs downward)
      return sortOrder === 'desc' ? comparison : -comparison;
    });
  }, [data, search, posFilter, sortBy, sortOrder, pinMaster]);

  return (
    <div>
      <div className="controls">
        <input 
          type="text" 
          className="search-input" 
          placeholder="Search by Account ID, Symbol or Side..." 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="select-input" value={posFilter} onChange={(e) => setPosFilter(e.target.value)}>
          <option value="all">All Positions</option>
          <option value="long">Net Long</option>
          <option value="short">Net Short</option>
          <option value="flat">Square Off</option>
        </select>
        <select className="select-input" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="pl">MTM (P&L)</option>
          <option value="volume">Volume (Qty)</option>
          <option value="buy_value">Buy Value ($)</option>
          <option value="trades">Trade Count</option>
          <option value="id">Account ID</option>
        </select>
        <select className="select-input" value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
          <option value="desc">Descending (High → Low)</option>
          <option value="asc">Ascending (Low → High)</option>
        </select>
        <select className="select-input" value={pinMaster ? 'yes' : 'no'} onChange={(e) => setPinMaster(e.target.value === 'yes')}>
          <option value="yes">Pin Master to Top</option>
          <option value="no">Sort Overall (No Pin)</option>
        </select>
      </div>

      <div className="list-header">
        <div>Account</div>
        <div>Net Position</div>
        <div>Volume</div>
        <div>Buy Value</div>
        <div>Sell Value</div>
        <div>Avg B / S</div>
        <div>MTM (P&L)</div>
        <div>Top Symbols</div>
        <div></div>
      </div>

      <div className="trader-list" style={{ gap: 0 }}>
        {filteredAndSortedData.map(trader => (
          <TraderRow key={trader.account} trader={trader} />
        ))}
      </div>
    </div>
  );
}
