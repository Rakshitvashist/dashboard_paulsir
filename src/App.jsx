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

  return (
    <>
      <nav className="top-nav">
        <div className="logo-area">
          <h1>INSTITUTIONAL DASHBOARD <span>V2.0 PRO (REACT)</span></h1>
        </div>
        <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>DATE: {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).toUpperCase()}</div>
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
