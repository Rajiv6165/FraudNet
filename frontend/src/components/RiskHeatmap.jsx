import React, { useMemo } from 'react';
import { Activity } from 'lucide-react';

const COUNTRIES = ['USA', 'GBR', 'CAN', 'IND', 'DEU', 'FRA', 'AUS', 'SGP', 'JPN', 'BRA'];
const CATEGORIES = ['retail', 'food', 'electronics', 'entertainment', 'travel', 'services', 'transfer'];

export default function RiskHeatmap({ metrics }) {
  // Aggregate metrics into a lookup dictionary: "COUNTRY_CATEGORY"
  const heatmapData = useMemo(() => {
    const data = {};
    
    // Initialize empty grid cells
    for (const c of COUNTRIES) {
      for (const cat of CATEGORIES) {
        data[`${c}_${cat}`] = {
          count: 0,
          flagged: 0,
          volume: 0,
          avgScore: 0.0
        };
      }
    }

    // Populate from backend metrics
    if (metrics && Array.isArray(metrics)) {
      metrics.forEach((m) => {
        const key = `${m.country}_${m.merchant_category}`;
        if (data[key]) {
          data[key].count += m.transaction_count;
          data[key].flagged += m.flagged_count;
          data[key].volume += parseFloat(m.total_volume || 0);
          // Simple average weighting
          data[key].avgScore = Math.max(data[key].avgScore, parseFloat(m.avg_risk_score || 0));
        }
      });
    }
    
    return data;
  }, [metrics]);

  // Helper to determine background color and opacity
  const getCellStyle = (cellData) => {
    if (cellData.count === 0) {
      return {
        background: 'rgba(255, 255, 255, 0.02)',
        borderColor: 'rgba(255, 255, 255, 0.03)'
      };
    }
    
    // Determine color base: Safe (Green) if 0 flagged, otherwise gradient to Red based on flagged density
    const flaggedRatio = cellData.count > 0 ? (cellData.flagged / cellData.count) : 0;
    
    if (cellData.flagged === 0) {
      // Scale green opacity slightly with volume/count
      const opacity = Math.min(0.5, 0.1 + (cellData.count / 100));
      return {
        background: `rgba(16, 185, 129, ${opacity})`,
        border: '1px solid rgba(16, 185, 129, 0.3)',
        boxShadow: cellData.count > 50 ? '0 0 8px rgba(16, 185, 129, 0.1)' : 'none'
      };
    } else {
      // Scale red/crimson opacity with flagged count and ratio
      const opacity = Math.min(0.9, 0.2 + (flaggedRatio * 0.4) + (cellData.flagged * 0.1));
      return {
        background: `rgba(239, 68, 68, ${opacity})`,
        border: '1px solid rgba(239, 68, 68, 0.5)',
        boxShadow: `0 0 10px rgba(239, 68, 68, ${opacity * 0.4})`
      };
    }
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-header">
        <div>
          <h2 className="panel-title">
            <Activity className="brand-icon" style={{ color: 'var(--primary)' }} />
            Risk Heatmap (Country × Category)
          </h2>
          <span className="panel-subtitle">Aggregated fraud density and volumes sourced from live_risk_dashboard</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowX: 'auto', paddingBottom: '8px' }}>
        {/* Heatmap Grid */}
        <div style={{ minWidth: '600px' }}>
          {/* Header Row */}
          <div className="heatmap-container" style={{ marginBottom: '6px' }}>
            <div className="heatmap-label"></div> {/* Corner Spacer */}
            {CATEGORIES.map((cat) => (
              <div key={cat} className="heatmap-label" style={{ fontWeight: '600', textTransform: 'capitalize' }}>
                {cat}
              </div>
            ))}
          </div>

          {/* Grid Rows */}
          {COUNTRIES.map((country) => (
            <div key={country} className="heatmap-container" style={{ marginBottom: '4px' }}>
              {/* Row Header Label */}
              <div className="heatmap-label row-header" style={{ fontWeight: '600' }}>
                {country}
              </div>

              {/* Cells */}
              {CATEGORIES.map((category) => {
                const key = `${country}_${category}`;
                const cellData = heatmapData[key];
                const cellStyle = getCellStyle(cellData);
                
                return (
                  <div
                    key={category}
                    className="heatmap-cell"
                    style={cellStyle}
                  >
                    {/* Small number count if flagged exists */}
                    {cellData.flagged > 0 && (
                      <span className="mono" style={{ fontSize: '10px', fontWeight: 'bold', color: '#fff' }}>
                        {cellData.flagged}
                      </span>
                    )}

                    {/* Rich Tooltip */}
                    <div className="heatmap-tooltip">
                      <div className="mono" style={{ fontWeight: 'bold', color: 'var(--secondary)', marginBottom: '4px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '2px' }}>
                        {country} • {category.toUpperCase()}
                      </div>
                      <div style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span>Total Tx: <strong>{cellData.count}</strong></span>
                        <span>Flagged: <strong style={{ color: cellData.flagged > 0 ? 'var(--color-danger)' : 'var(--color-safe)' }}>{cellData.flagged}</strong></span>
                        <span>Volume: <strong>${cellData.volume.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></span>
                        <span>Risk Peak: <strong>{cellData.avgScore.toFixed(2)}</strong></span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      
      {/* Legend */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '16px', marginTop: '16px', fontSize: '11px', color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '12px', height: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '2px' }}></div>
          <span>No Activity</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '12px', height: '12px', background: 'rgba(16, 185, 129, 0.3)', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: '2px' }}></div>
          <span>Safe Transactions</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '12px', height: '12px', background: 'rgba(239, 68, 68, 0.6)', border: '1px solid rgba(239, 68, 68, 0.8)', borderRadius: '2px', boxShadow: '0 0 5px rgba(239,68,68,0.3)' }}></div>
          <span>Flagged Fraud</span>
        </div>
      </div>
    </div>
  );
}
