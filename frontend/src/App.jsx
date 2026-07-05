import React, { useState, useEffect, useRef } from 'react';
import { Shield, Play, Square, RefreshCw, Layers, Radio, Globe } from 'lucide-react';
import LiveFeed from './components/LiveFeed';
import RiskHeatmap from './components/RiskHeatmap';
import FraudRingGraph from './components/FraudRingGraph';
import TransactionDrawer from './components/TransactionDrawer';

export default function App() {
  const [transactions, setTransactions] = useState([]);
  const [rings, setRings] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [selectedTx, setSelectedTx] = useState(null);
  
  const [simRunning, setSimRunning] = useState(false);
  const [simSpeed, setSimSpeed] = useState(2.0);
  const [wsStatus, setWsStatus] = useState('disconnected');
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const WS_URL = API_URL.replace(/^http/, 'ws');

  // Fetch initial dashboard state
  const fetchDashboardData = async () => {
    try {
      const [resRings, resMetrics] = await Promise.all([
        fetch(`${API_URL}/rings`),
        fetch(`${API_URL}/dashboard/metrics`)
      ]);
      if (resRings.ok) {
        const ringsData = await resRings.json();
        setRings(ringsData);
      }
      if (resMetrics.ok) {
        const metricsData = await resMetrics.json();
        setMetrics(metricsData);
      }
    } catch (e) {
      console.error('Error fetching initial dashboard data:', e);
    }
  };

  // Connect to WebSocket streaming feed
  const connectWebSocket = () => {
    if (wsRef.current) wsRef.current.close();
    setWsStatus('connecting');

    const ws = new WebSocket(`${WS_URL}/ws/live-feed`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket Connected');
      setWsStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const txWithScore = JSON.parse(event.data);
        
        // Append to front of list
        setTransactions((prev) => {
          // Keep only last 50 transactions
          const updated = [txWithScore, ...prev];
          return updated.slice(0, 50);
        });

        // Trigger an incremental fetch to get updated rings and heatmap metrics
        fetchDashboardData();
      } catch (e) {
        console.error('Error processing websocket message:', e);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket Disconnected. Reconnecting...');
      setWsStatus('disconnected');
      // Exponential backoff or simple reconnect after 3s
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      ws.close();
    };
  };

  useEffect(() => {
    fetchDashboardData();
    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, []);

  // Simulator controls
  const handleStartSimulator = async () => {
    try {
      const res = await fetch(`${API_URL}/simulator/start?speed=${simSpeed}`, {
        method: 'POST'
      });
      if (res.ok) {
        setSimRunning(true);
      }
    } catch (e) {
      console.error('Failed to start simulator:', e);
    }
  };

  const handleStopSimulator = async () => {
    try {
      const res = await fetch(`${API_URL}/simulator/stop`, {
        method: 'POST'
      });
      if (res.ok) {
        setSimRunning(false);
      }
    } catch (e) {
      console.error('Failed to stop simulator:', e);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Top Header */}
      <header className="dashboard-header">
        <div className="brand">
          <Shield className="brand-icon" style={{ color: 'var(--primary)' }} />
          <h1>FraudNet</h1>
          <span style={{ fontSize: '12px', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border-color)', fontWeight: 'bold' }}>
            SQL-Native Real-Time Fraud Engine
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {/* Simulator status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Simulation:</span>
            {simRunning ? (
              <span className="status-badge">
                <span className="status-indicator" />
                Active ({simSpeed}/s)
              </span>
            ) : (
              <span className="status-badge offline">
                <span className="status-indicator offline" />
                Inactive
              </span>
            )}
          </div>

          {/* WebSocket status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Socket DSN:</span>
            {wsStatus === 'connected' ? (
              <span className="status-badge" style={{ color: 'var(--secondary)', border: '1px solid rgba(20,184,166,0.2)', background: 'rgba(20,184,166,0.05)' }}>
                Streaming
              </span>
            ) : (
              <span className="status-badge offline">
                {wsStatus === 'connecting' ? 'Connecting...' : 'Closed'}
              </span>
            )}
          </div>

          {/* Manual Refresh */}
          <button 
            onClick={fetchDashboardData}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
            title="Refresh aggregates"
            className="control-btn secondary"
          >
            <RefreshCw size={14} />
            <span>Sync</span>
          </button>
        </div>
      </header>

      {/* Grid Dashboard */}
      <main className="dashboard-grid">
        {/* Row 1: Controls panel & Aggregations */}
        <div className="panel col-span-2" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Radio size={20} style={{ color: 'var(--secondary)' }} />
              Control Panel & Live Simulator
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Spin up the generator to replay transactions and watch database triggers execute velocity, deviation, and graph scoring at commit.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Speed selection */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginRight: '8px' }}>
              <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Velocity:</label>
              <select 
                value={simSpeed} 
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setSimSpeed(val);
                  if (simRunning) {
                    fetch(`${API_URL}/simulator/start?speed=${val}`, { method: 'POST' });
                  }
                }}
                style={{
                  background: '#090d1a',
                  border: '1px solid var(--border-color)',
                  color: '#fff',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '13px',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                <option value={0.5}>0.5 tx/s (Slow)</option>
                <option value={1.0}>1.0 tx/s (Normal)</option>
                <option value={2.0}>2.0 tx/s (Fast)</option>
                <option value={5.0}>5.0 tx/s (Intense)</option>
              </select>
            </div>

            {simRunning ? (
              <button className="control-btn danger" onClick={handleStopSimulator}>
                <Square size={16} />
                Stop Replay
              </button>
            ) : (
              <button className="control-btn" onClick={handleStartSimulator}>
                <Play size={16} />
                Replay Attack Simulator
              </button>
            )}
          </div>
        </div>

        {/* Row 2: Live Ingestion Stream & Heatmap Matrix */}
        <div style={{ minHeight: '550px' }}>
          <LiveFeed 
            transactions={transactions} 
            onSelectTransaction={setSelectedTx} 
          />
        </div>

        <div style={{ minHeight: '550px' }}>
          <RiskHeatmap metrics={metrics} />
        </div>

        {/* Row 3: Graph Network Visualizer */}
        <div className="col-span-2" style={{ minHeight: '450px' }}>
          <FraudRingGraph rings={rings} transactions={transactions} />
        </div>
      </main>

      {/* Slide-in details Drawer */}
      <TransactionDrawer 
        transaction={selectedTx} 
        onClose={() => setSelectedTx(null)} 
      />

      {/* Footer */}
      <footer style={{ marginTop: 'auto', padding: '24px 40px', borderTop: '1px solid var(--border-color)', textAlign: 'center', fontSize: '12px', color: 'var(--text-dim)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>FraudNet Risk Visualization Engine v1.0.0</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Globe size={12} />
          PostgreSQL 16 PL/pgSQL Triggers • FastAPI Async Streams • Canvas 2D Physics Engine
        </span>
      </footer>
    </div>
  );
}
