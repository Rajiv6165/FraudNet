import React from 'react';
import { X, User, AlertTriangle, ShieldCheck, ShieldAlert, Cpu, Database, Network } from 'lucide-react';

export default function TransactionDrawer({ transaction, onClose }) {
  if (!transaction) return null;

  const composite = parseFloat(transaction.composite_score || 0);
  const velocity = parseFloat(transaction.velocity_score || 0);
  const deviation = parseFloat(transaction.deviation_score || 0);
  const ring = parseFloat(transaction.ring_score || 0);
  const isHighRisk = composite >= 0.75;

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const getSeverityLabel = (score) => {
    if (score < 0.3) return <span style={{ color: 'var(--color-safe)' }}>Safe / Low Risk</span>;
    if (score < 0.75) return <span style={{ color: 'var(--color-warn)' }}>Suspicious / Medium Risk</span>;
    return <span style={{ color: 'var(--color-danger)', fontWeight: 'bold' }}>SEVERE FRAUD / High Risk</span>;
  };

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {isHighRisk ? (
              <ShieldAlert size={24} style={{ color: 'var(--color-danger)' }} />
            ) : (
              <ShieldCheck size={24} style={{ color: 'var(--color-safe)' }} />
            )}
            <h3 style={{ fontSize: '18px', fontWeight: 'bold' }}>Transaction Analysis</h3>
          </div>
          <button className="drawer-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="drawer-body">
          {/* Risk Level Callout */}
          <div 
            style={{ 
              background: isHighRisk ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)',
              border: `1px solid ${isHighRisk ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`,
              borderRadius: '10px',
              padding: '16px',
              marginBottom: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Composite Risk Score
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span className="mono" style={{ fontSize: '32px', fontWeight: 'bold', color: isHighRisk ? 'var(--color-danger)' : 'var(--color-safe)' }}>
                {composite.toFixed(2)}
              </span>
              <span style={{ fontSize: '14px' }}>
                {getSeverityLabel(composite)}
              </span>
            </div>
          </div>

          {/* Details Section */}
          <div style={{ marginBottom: '24px' }}>
            <h4 style={{ fontSize: '14px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>
              Transaction Parameters
            </h4>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <tbody>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>Amount</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: '600', fontSize: '15px' }}>{formatCurrency(transaction.amount)}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>Merchant</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: '500' }}>{transaction.merchant}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>Category</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{transaction.merchant_category}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>User Name</td>
                  <td style={{ padding: '8px 0', textAlign: 'right' }}>{transaction.user_name || `User #${transaction.user_id}`}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>Tx Country / Home</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{transaction.country} / {transaction.home_country || 'USA'}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>Device Fingerprint</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#fff', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '240px' }} title={transaction.device_id}>
                    {transaction.device_id}
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>IP Address</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{transaction.ip_address}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>Timestamp</td>
                  <td style={{ padding: '8px 0', textAlign: 'right' }}>{new Date(transaction.created_at).toLocaleString()}</td>
                </tr>
                <tr>
                  <td style={{ padding: '8px 0', color: 'var(--text-muted)' }}>Transaction ID</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)' }}>{transaction.transaction_id || transaction.id}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Scoring Factors Breakdown */}
          <div>
            <h4 style={{ fontSize: '14px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>
              Multi-Factor Risk Analysis
            </h4>
            
            <div className="factor-list">
              {/* Velocity Score */}
              <div className="factor-item">
                <div className="factor-title-row">
                  <span style={{ fontWeight: '500', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Cpu size={14} style={{ color: 'var(--primary)' }} />
                    Velocity Velocity Score
                  </span>
                  <span className="mono" style={{ fontWeight: '600' }}>{velocity.toFixed(2)}</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Rolling count and spend amounts over 10m/1h/24h compared to history.
                </div>
                <div className="factor-progress-bar">
                  <div 
                    className="factor-progress-fill primary" 
                    style={{ width: `${velocity * 100}%` }}
                  />
                </div>
              </div>

              {/* Deviation Score */}
              <div className="factor-item">
                <div className="factor-title-row">
                  <span style={{ fontWeight: '500', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Database size={14} style={{ color: 'var(--secondary)' }} />
                    Behavioral Deviation
                  </span>
                  <span className="mono" style={{ fontWeight: '600' }}>{deviation.toFixed(2)}</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Z-score amount deviation and novelty flags for country or merchant category.
                </div>
                <div className="factor-progress-bar">
                  <div 
                    className="factor-progress-fill secondary" 
                    style={{ width: `${deviation * 100}%` }}
                  />
                </div>
              </div>

              {/* Ring Score */}
              <div className="factor-item">
                <div className="factor-title-row">
                  <span style={{ fontWeight: '500', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Network size={14} style={{ color: 'var(--color-danger)' }} />
                    Fraud Ring Association
                  </span>
                  <span className="mono" style={{ fontWeight: '600' }}>{ring.toFixed(2)}</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Recursive cluster tracing identifying links to other users via device, IP, or card.
                </div>
                <div className="factor-progress-bar">
                  <div 
                    className="factor-progress-fill danger" 
                    style={{ width: `${ring * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
          
          <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: '8px', border: '1px dashed var(--border-color)', fontSize: '11px', color: 'var(--text-dim)', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <span>
              All scores calculated in PostgreSQL at transaction commit. Composite formula: 
              <br /><code className="mono" style={{ color: 'var(--text-muted)' }}>(velocity*0.3) + (deviation*0.4) + (ring*0.3)</code>
            </span>
          </div>

        </div>
      </div>
    </>
  );
}
