import React, { useState } from 'react';
import { FinancialEvidenceGraph, GraphNode } from '../../types/evidenceGraph';
import { FileText, Building2, ShoppingBag, Truck, CreditCard, Landmark, BookOpen, Layers } from 'lucide-react';

interface EvidenceGraphProps {
  graph: FinancialEvidenceGraph;
  onSelectNode?: (node: GraphNode) => void;
}

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({ graph, onSelectNode }) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Position nodes radially or topologically
  const nodePositions: Record<string, { x: number; y: number }> = {
    'node-vendor': { x: 100, y: 150 },
    'node-inv': { x: 320, y: 150 },
    'node-po': { x: 320, y: 50 },
    'node-pay-1': { x: 550, y: 60 },
    'node-pay-2': { x: 550, y: 120 },
    'node-pay-3': { x: 550, y: 180 },
    'node-pay-4': { x: 550, y: 240 },
    'node-bank': { x: 740, y: 150 },
    'node-gl': { x: 320, y: 260 },
  };

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'vendor': return <Building2 size={16} />;
      case 'invoice': return <FileText size={16} />;
      case 'purchase_order': return <ShoppingBag size={16} />;
      case 'goods_receipt': return <Truck size={16} />;
      case 'payment': return <CreditCard size={16} />;
      case 'bank_account': return <Landmark size={16} />;
      case 'gl_account': return <BookOpen size={16} />;
      default: return <Layers size={16} />;
    }
  };

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'vendor': return 'var(--color-neutral-800)';
      case 'invoice': return 'var(--color-primary-500)';
      case 'purchase_order': return 'var(--color-secondary-600)';
      case 'goods_receipt': return 'var(--color-accent-600)';
      case 'payment': return 'var(--color-primary-600)';
      case 'bank_account': return 'var(--color-info)';
      case 'gl_account': return 'var(--color-neutral-700)';
      default: return 'var(--color-neutral-600)';
    }
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '340px',
        background: '#fafafa',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-neutral-200)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: '0.75rem',
          left: '1rem',
          fontSize: '0.72rem',
          fontWeight: 700,
          color: 'var(--color-neutral-400)',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <span>Directed Evidence Graph (PageRank Relevance Sizing)</span>
        <span style={{ background: 'var(--color-neutral-200)', padding: '0.1rem 0.4rem', borderRadius: 'var(--radius-full)', color: 'var(--color-neutral-700)' }}>
          {graph.nodes.length} Nodes • {graph.edges.length} Edges
        </span>
      </div>

      <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="16"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="var(--color-neutral-300)" />
          </marker>
        </defs>

        {/* Directed Edges */}
        {graph.edges.map((edge) => {
          const source = nodePositions[edge.source] || { x: 200, y: 100 };
          const target = nodePositions[edge.target] || { x: 400, y: 200 };
          const midX = (source.x + target.x) / 2;
          const midY = (source.y + target.y) / 2;

          return (
            <g key={edge.id}>
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="var(--color-neutral-300)"
                strokeWidth="1.5"
                strokeDasharray="4 2"
                markerEnd="url(#arrowhead)"
              />
              <text
                x={midX}
                y={midY - 4}
                fill="var(--color-neutral-400)"
                fontSize="8px"
                fontWeight="700"
                textAnchor="middle"
                fontFamily="var(--font-family-mono)"
              >
                {edge.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Nodes */}
      {graph.nodes.map((node) => {
        const pos = nodePositions[node.id] || { x: 250, y: 150 };
        const isSelected = selectedNodeId === node.id;
        const color = getNodeColor(node.type);
        const score = node.pagerank_score || 0.7;
        const nodeSize = 44 + Math.round(score * 16);

        return (
          <div
            key={node.id}
            onClick={() => {
              setSelectedNodeId(node.id);
              if (onSelectNode) onSelectNode(node);
            }}
            style={{
              position: 'absolute',
              left: `${pos.x}px`,
              top: `${pos.y}px`,
              transform: 'translate(-50%, -50%)',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              zIndex: 10,
            }}
          >
            {/* Node Circle */}
            <div
              style={{
                width: `${nodeSize}px`,
                height: `${nodeSize}px`,
                borderRadius: '50%',
                background: '#ffffff',
                border: `2px solid ${isSelected ? 'var(--color-neutral-950)' : color}`,
                boxShadow: isSelected ? '0 0 0 4px rgba(0,0,0,0.1), 0 8px 16px rgba(0,0,0,0.15)' : 'var(--shadow-sm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: color,
                transition: 'all var(--transition-fast)',
              }}
            >
              {getNodeIcon(node.type)}
            </div>

            {/* Label */}
            <div
              style={{
                marginTop: '0.35rem',
                fontSize: '0.68rem',
                fontWeight: 700,
                color: 'var(--color-neutral-800)',
                background: '#ffffff',
                padding: '0.1rem 0.4rem',
                borderRadius: 'var(--radius-xs)',
                boxShadow: 'var(--shadow-sm)',
                whiteSpace: 'nowrap',
                maxWidth: '140px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {node.label}
            </div>
          </div>
        );
      })}
    </div>
  );
};
