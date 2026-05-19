import React, { useEffect, useState } from 'react';
import GlobalSummary from './components/GlobalSummary.jsx';
import SymbolSummary from './components/SymbolSummary.jsx';
import TraderList from './components/TraderList.jsx';

function App() {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let lastDataHash = '';

    const loadData = async () => {
      try {
        const path = window.location.pathname.endsWith('/') ? 'trader_data.json' : './trader_data.json';
        const res = await fetch(path);
        
        if (!res.ok) throw new Error(`HTTP Error: ${res.status} - ${res.statusText}`);
        
        const resText = await res.text();
        
        if (resText !== lastDataHash) {
          lastDataHash = resText;
          setData(JSON.parse(resText));
        }
        
        setError(null);
        setIsLoading(false);
      } catch (err) {
        console.error("Dashboard update error:", err);
        if (data.length === 0) {
          setError(err.message);
          setIsLoading(false);
        }
      }
    };

    loadData();
    const interval = setInterval(loadData, 1000);
    return () => clearInterval(interval);
  }, []); // Run once on mount

  if (isLoading) {
    return (
      <div className="loader-overlay">
        <div style={{ width: '40px', height: '40px', border: '4px solid #e2e8f0', borderTopColor: '#1e293b', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
        <div className="loading-text">Initialising Global Dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-debugger" style={{ display: 'block' }}>
        <strong>Data Load Failed</strong><br/>
        Error: {error}<br/><br/>
        <em>Tip: Ensure 'trader_data.json' is available.</em>
      </div>
    );
  }

  const handleExportExcel = () => {
    if (!data || data.length === 0) return;
    
    let csvContent = "";
    
    // 1. Title & Metadata
    csvContent += `INSTITUTIONAL RISK DASHBOARD - EXPORTED DATA\n`;
    csvContent += `Export Date,${new Date().toLocaleString()}\n\n`;
    
    // 2. Global Risk Summary
    const totalBuy = data.reduce((acc, t) => acc + (t.total_buy_qty || 0), 0);
    const totalSell = data.reduce((acc, t) => acc + (t.total_sell_qty || 0), 0);
    const totalMtm = data.reduce((acc, t) => acc + (t.gross_pl || 0), 0);
    const masterMtm = data.find(t => t.is_master)?.gross_pl || 0;
    
    csvContent += `GLOBAL RISK SUMMARY\n`;
    csvContent += `Metric,Value\n`;
    csvContent += `Total Volume,${totalBuy + totalSell}\n`;
    csvContent += `Global MTM P&L,${totalMtm.toFixed(2)}\n`;
    csvContent += `Master MTM (XOF9000),${masterMtm.toFixed(2)}\n\n`;
    
    // 3. Trader Performance Summary
    csvContent += `TRADER PERFORMANCE SUMMARY\n`;
    csvContent += `Account,Name,Backcode,Total Buy Qty,Total Sell Qty,Net Position,MTM P&L,Trades Count,Volatility\n`;
    data.forEach(t => {
      csvContent += `"${t.account}","${t.name}","${t.backcode}",${t.total_buy_qty},${t.total_sell_qty},${t.net_position},${t.gross_pl.toFixed(2)},${t.num_trades},${(t.volatility || 0).toFixed(4)}\n`;
    });
    csvContent += `\n`;
    
    // 4. Contract-Wise Open Positions
    csvContent += `CONTRACT-WISE OPEN POSITIONS\n`;
    csvContent += `Account,Name,Scrip,Exchange,Expiry,Call/Put,Strike,Brought Forward Qty,Buy Qty,Sell Qty,Net Qty,Average Rate,LTP,MTM P&L\n`;
    data.forEach(t => {
      if (t.positions && t.positions.length > 0) {
        t.positions.forEach(p => {
          csvContent += `"${t.account}","${t.name}","${p.scrip_name}","${p.exchange}","${p.expiry_date}","${p.callput}",${p.strike},${p.bf_qty},${p.buy_qty},${p.sell_qty},${p.net_qty},${p.average_rate.toFixed(4)},${p.ltp.toFixed(4)},${p.mtm.toFixed(2)}\n`;
        });
      }
    });
    csvContent += `\n`;
    
    // 5. Raw Execution Logs
    csvContent += `TODAY'S EXECUTION LOG\n`;
    csvContent += `Account,Name,Time,Symbol,Side,Qty,Price,Value,Exchange,Expiry\n`;
    data.forEach(t => {
      if (t.trades && t.trades.length > 0) {
        t.trades.forEach(tr => {
          csvContent += `"${t.account}","${t.name}","${tr.Time}","${tr.Symbol}","${tr.Side}",${tr.Qty},${tr.Price.toFixed(4)},${tr.Value.toFixed(2)},"${tr.Exchange}","${tr.Expiry || ''}"\n`;
        });
      }
    });
    
    // Create download link with BOM for perfect Excel UTF-8 support
    const blob = new Blob(["\ufeff" + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    
    const dateStr = new Date().toISOString().split('T')[0];
    link.download = `Institutional_Risk_Report_${dateStr}.csv`;
    
    document.body.appendChild(link);
    link.click();
    
    // Clean up asynchronously to allow download engine to initialize successfully
    setTimeout(() => {
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }, 200);
  };

  return (
    <>
      <nav className="top-nav">
        <div className="logo-area">
          <h1>INSTITUTIONAL DASHBOARD <span>V2.0 PRO (REACT)</span></h1>
        </div>
        <div className="header-right">
          <div className="header-date">DATE: {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).toUpperCase()}</div>
          <button onClick={handleExportExcel} className="export-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export Excel
          </button>
        </div>
      </nav>

      <div className="container">
        <GlobalSummary data={data} />
        <SymbolSummary data={data} />
        <TraderList data={data} />
      </div>
    </>
  );
}

export default App;
