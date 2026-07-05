import React, { useRef, useEffect } from 'react';
import { Shield, ShieldAlert, ArrowUpRight } from 'lucide-react';

export default function LiveFeed({ transactions, onSelectTransaction }) {
  const containerRef = useRef(null);

  // Helper to format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  // Helper to format time
  const formatTime = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (e) {
      return dateStr;
    }
  };

  // Helper to get risk score color badge
  const getRiskBadge = (score) => {
    const s = parseFloat(score);
    if (s < 0.3) return <span className="risk-badge safe">Safe ({s.toFixed(2)})</span>;
    if (s < 0.75) return <span className="risk-badge warn">Suspect ({s.toFixed(2)})</span>;
    return <span className="risk-badge danger">Fraud ({s.toFixed(2)})</span>;
  };

  return (
    <div className="panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', maxHeight: '550px' }}>
      <div className="panel-header">
        <div>
          <h2 className="panel-title">
            <Shield className="brand-icon" style={{ color: 'var(--secondary)' }} />
            Live Ingestion Stream
          </h2>
          <span className="panel-subtitle">Real-time ledger events streamed from PostgreSQL triggers</span>
        </div>
        <span className="mono" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {transactions.length} active
        </span>
      </div>

      <div 
        ref={containerRef}
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '8px', 
          paddingRight: '4px' 
        }}
      >
        {transactions.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, color: 'var(--text-dim)', gap: '12px' }}>
            <ShieldAlert size={36} />
            <p>Awaiting transactions. Click Replay Simulator to start feed.</p>
          </div>
        ) : (
          transactions.map((tx) => {
            const composite = parseFloat(tx.composite_score || 0);
            const isHighRisk = composite >= 0.75;
            
            return (
              <div 
                key={tx.transaction_id || tx.id}
                onClick={() => onSelectTransaction(tx)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: isHighRisk ? 'rgba(239, 68, 68, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                  border: isHighRisk 
                    ? '1px solid rgba(239, 68, 68, 0.2)' 
                    : '1px solid var(--border-color)',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                className="feed-item"
              >
                <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                  <div className="mono" style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                    {formatTime(tx.created_at)}
                  </div>
                  <div>
                    <div style={{ fontWeight: '500', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {tx.user_name || `User #${tx.user_id}`}
                      <span className="mono" style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                        ({tx.country})
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {tx.merchant} • <span className="mono" style={{ fontSize: '11px' }}>{tx.merchant_category}</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: '600', fontSize: '15px' }}>
                      {formatCurrency(tx.amount)}
                    </div>
                    <div style={{ marginTop: '4px' }}>
                      {getRiskBadge(tx.composite_score)}
                    </div>
                  </div>
                  <ArrowUpRight size={16} style={{ color: 'var(--text-dim)' }} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
