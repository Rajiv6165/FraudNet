import React, { useEffect, useRef, useState, useMemo } from 'react';
import { GitBranch, Info } from 'lucide-react';

export default function FraudRingGraph({ rings, transactions }) {
  const canvasRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const animationRef = useRef(null);

  // Parse rings data into nodes and links
  const graphData = useMemo(() => {
    if (!rings || !Array.isArray(rings) || rings.length === 0) {
      return { nodes: [], links: [] };
    }

    const nodesMap = {};
    const links = [];

    // Group by ring_id
    const ringsGrouped = {};
    rings.forEach((r) => {
      if (!ringsGrouped[r.ring_id]) {
        ringsGrouped[r.ring_id] = [];
      }
      ringsGrouped[r.ring_id].push(r);
    });

    // Color palette for different rings
    const ringColors = [
      '#ef4444', // Red
      '#f59e0b', // Orange
      '#ec4899', // Pink
      '#a855f7', // Purple
      '#3b82f6', // Blue
      '#06b6d4', // Cyan
    ];

    let ringColorIdx = 0;

    Object.entries(ringsGrouped).forEach(([ringId, members]) => {
      const color = ringColors[ringColorIdx % ringColors.length];
      ringColorIdx++;

      // Create nodes
      members.forEach((m, idx) => {
        nodesMap[m.user_id] = {
          id: m.user_id,
          ringId: ringId,
          size: m.ring_size,
          volume: parseFloat(m.ring_volume),
          color: color,
          // Starting coordinates (spread out in circle)
          x: 200 + 120 * Math.cos((idx / members.length) * 2 * Math.PI) + Math.random() * 20,
          y: 190 + 120 * Math.sin((idx / members.length) * 2 * Math.PI) + Math.random() * 20,
          vx: 0,
          vy: 0,
          radius: 12 + Math.min(10, m.ring_size) // larger size = bigger node
        };
      });

      // Fully connect all members within this ring (clique connection)
      for (let i = 0; i < members.length; i++) {
        for (let j = i + 1; j < members.length; j++) {
          links.push({
            source: members[i].user_id,
            target: members[j].user_id,
            ringId: ringId,
            color: color + '40' // semi-transparent link
          });
        }
      }
    });

    return {
      nodes: Object.values(nodesMap),
      links: links
    };
  }, [rings]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width = canvas.offsetWidth;
    let height = canvas.offsetHeight;
    
    // Set internal resolution matching DOM size
    canvas.width = width;
    canvas.height = height;

    const { nodes, links } = graphData;

    // Physics constants
    const repulsion = 140;
    const attraction = 0.04;
    const centerGravity = 0.015;
    const damping = 0.85;

    // Simulation loop
    const tick = () => {
      if (nodes.length === 0) return;

      // 1. Calculate repulsion forces (Coulomb's Law-like)
      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const distSq = dx * dx + dy * dy + 0.1;
          const dist = Math.sqrt(distSq);
          
          if (dist < 180) { // Repulsion range
            const force = repulsion / distSq;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            
            n1.vx -= fx;
            n1.vy -= fy;
            n2.vx += fx;
            n2.vy += fy;
          }
        }
      }

      // 2. Calculate attraction forces along links (Hooke's Law spring)
      links.forEach((link) => {
        const sourceNode = nodes.find((n) => n.id === link.source);
        const targetNode = nodes.find((n) => n.id === link.target);
        if (!sourceNode || !targetNode) return;

        const dx = targetNode.x - sourceNode.x;
        const dy = targetNode.y - sourceNode.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.1;
        
        // Spring target length
        const targetLen = 80;
        const force = (dist - targetLen) * attraction;
        
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        sourceNode.vx += fx;
        sourceNode.vy += fy;
        targetNode.vx -= fx;
        targetNode.vy -= fy;
      });

      // 3. Gravity force pulling to center, update coordinates, boundary check
      const centerX = width / 2;
      const centerY = height / 2;

      nodes.forEach((node) => {
        // Gravity to center
        node.vx += (centerX - node.x) * centerGravity;
        node.vy += (centerY - node.y) * centerGravity;

        // Apply velocity & damping
        node.x += node.vx;
        node.y += node.vy;
        node.vx *= damping;
        node.vy *= damping;

        // Keep inside canvas bounds
        node.x = Math.max(node.radius, Math.min(width - node.radius, node.x));
        node.y = Math.max(node.radius, Math.min(height - node.radius, node.y));
      });

      // 4. Render
      ctx.clearRect(0, 0, width, height);

      // Draw connection links
      ctx.lineWidth = 1.5;
      links.forEach((link) => {
        const sourceNode = nodes.find((n) => n.id === link.source);
        const targetNode = nodes.find((n) => n.id === link.target);
        if (!sourceNode || !targetNode) return;

        ctx.strokeStyle = link.color;
        ctx.beginPath();
        ctx.moveTo(sourceNode.x, sourceNode.y);
        ctx.lineTo(targetNode.x, targetNode.y);
        ctx.stroke();
      });

      // Draw nodes
      nodes.forEach((node) => {
        // Glow effect
        ctx.shadowBlur = 12;
        ctx.shadowColor = node.color;
        
        // Node fill
        ctx.fillStyle = node.color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
        ctx.fill();

        // Node border
        ctx.shadowBlur = 0; // reset shadow
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#060913';
        ctx.stroke();

        // Node User ID text
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold 10px ${getComputedStyle(document.documentElement).getPropertyValue('--font-mono')}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`U${node.id}`, node.x, node.y);
      });

      animationRef.current = requestAnimationFrame(tick);
    };

    tick();

    // Resize handler
    const handleResize = () => {
      if (!canvasRef.current) return;
      width = canvasRef.current.offsetWidth;
      height = canvasRef.current.offsetHeight;
      canvasRef.current.width = width;
      canvasRef.current.height = height;
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationRef.current);
      window.removeEventListener('resize', handleResize);
    };
  }, [graphData]);

  // Handle canvas click to select a node
  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Check if clicked any node
    let clickedNode = null;
    graphData.nodes.forEach((node) => {
      const dx = node.x - clickX;
      const dy = node.y - clickY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist <= node.radius + 5) {
        clickedNode = node;
      }
    });

    setSelectedNode(clickedNode);
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-header">
        <div>
          <h2 className="panel-title">
            <GitBranch className="brand-icon" style={{ color: 'var(--color-danger)' }} />
            Fraud Ring Graph
          </h2>
          <span className="panel-subtitle">Recursive attribute linking (device, IP, card) forming threat clusters</span>
        </div>
      </div>

      <div className="graph-canvas-container" style={{ position: 'relative' }}>
        <canvas 
          ref={canvasRef} 
          onClick={handleCanvasClick}
          style={{ width: '100%', height: '100%', cursor: 'pointer', display: 'block' }}
        />

        {selectedNode ? (
          <div 
            style={{ 
              position: 'absolute', 
              bottom: '12px', 
              left: '12px', 
              right: '12px',
              background: 'rgba(9, 13, 26, 0.9)', 
              border: `1px solid ${selectedNode.color}`, 
              borderRadius: '8px', 
              padding: '12px',
              backdropFilter: 'blur(8px)',
              fontSize: '12px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <strong style={{ color: selectedNode.color, fontFamily: 'var(--font-mono)' }}>
                User ID: #{selectedNode.id}
              </strong>
              <button 
                onClick={() => setSelectedNode(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontFamily: 'var(--font-mono)' }}>
              <div>Ring ID: <span style={{ color: '#fff' }}>{selectedNode.ringId}</span></div>
              <div>Ring Size: <span style={{ color: '#fff' }}>{selectedNode.size} members</span></div>
              <div style={{ gridColumn: 'span 2' }}>
                Accumulated Volume:{' '}
                <span style={{ color: 'var(--color-danger)', fontWeight: 'bold' }}>
                  ${selectedNode.volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div 
            style={{ 
              position: 'absolute', 
              top: '12px', 
              right: '12px', 
              background: 'rgba(255,255,255,0.03)', 
              padding: '6px 10px', 
              borderRadius: '6px', 
              fontSize: '11px', 
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              border: '1px solid var(--border-color)',
              pointerEvents: 'none'
            }}
          >
            <Info size={12} />
            <span>Click nodes to analyze</span>
          </div>
        )}

        {graphData.nodes.length === 0 && (
          <div 
            style={{ 
              position: 'absolute', 
              top: '50%', 
              left: '50%', 
              transform: 'translate(-50%, -50%)', 
              color: 'var(--text-dim)', 
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <GitBranch size={32} />
            <span>No fraud rings currently active in ledger</span>
          </div>
        )}
      </div>
    </div>
  );
}
