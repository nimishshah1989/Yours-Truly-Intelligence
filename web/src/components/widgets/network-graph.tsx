"use client";

import { useMemo, useState, useCallback } from "react";
import { getChartColor } from "@/lib/chart-config";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GraphNode {
  id: string;
  label: string;
  value: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
  radius: number;
}

interface NetworkGraphProps {
  data: Record<string, unknown>;
  config?: Record<string, unknown>;
}

interface TooltipState {
  node: PositionedNode;
  x: number;
  y: number;
}

// ---------------------------------------------------------------------------
// Force simulation — runs once on mount, ~100 iterations
// ---------------------------------------------------------------------------

function runForceLayout(nodes: GraphNode[], edges: GraphEdge[], width: number, height: number): PositionedNode[] {
  const cx = width / 2;
  const cy = height / 2;
  const maxVal = Math.max(...nodes.map((n) => n.value), 1);

  // Initialize positions in a circle
  const positioned: PositionedNode[] = nodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.length;
    const spread = Math.min(width, height) * 0.3;
    return {
      ...n,
      x: cx + Math.cos(angle) * spread,
      y: cy + Math.sin(angle) * spread,
      radius: Math.max(8, Math.sqrt(n.value / maxVal) * 28),
    };
  });

  const nodeMap = new Map(positioned.map((n) => [n.id, n]));

  // Run simple spring simulation
  const ITERATIONS = 80;
  const REPULSION = 2000;
  const ATTRACTION = 0.005;
  const DAMPING = 0.9;
  const velocities = new Map(positioned.map((n) => [n.id, { vx: 0, vy: 0 }]));

  for (let iter = 0; iter < ITERATIONS; iter++) {
    // Repulsion between all node pairs
    for (let i = 0; i < positioned.length; i++) {
      for (let j = i + 1; j < positioned.length; j++) {
        const a = positioned[i];
        const b = positioned[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const force = REPULSION / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const va = velocities.get(a.id)!;
        const vb = velocities.get(b.id)!;
        va.vx += fx;
        va.vy += fy;
        vb.vx -= fx;
        vb.vy -= fy;
      }
    }

    // Attraction along edges
    for (const edge of edges) {
      const a = nodeMap.get(edge.source);
      const b = nodeMap.get(edge.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const force = dist * ATTRACTION * edge.weight;
      const fx = (dx / Math.max(dist, 1)) * force;
      const fy = (dy / Math.max(dist, 1)) * force;
      velocities.get(a.id)!.vx += fx;
      velocities.get(a.id)!.vy += fy;
      velocities.get(b.id)!.vx -= fx;
      velocities.get(b.id)!.vy -= fy;
    }

    // Center gravity
    for (const node of positioned) {
      const v = velocities.get(node.id)!;
      v.vx += (cx - node.x) * 0.001;
      v.vy += (cy - node.y) * 0.001;
    }

    // Apply velocities + damping
    for (const node of positioned) {
      const v = velocities.get(node.id)!;
      v.vx *= DAMPING;
      v.vy *= DAMPING;
      node.x = Math.max(node.radius + 10, Math.min(width - node.radius - 10, node.x + v.vx));
      node.y = Math.max(node.radius + 10, Math.min(height - node.radius - 10, node.y + v.vy));
    }
  }

  return positioned;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function NetworkGraphWidget({ data }: NetworkGraphProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const graphData = data as unknown as GraphData;
  const nodes = graphData?.nodes ?? [];
  const edges = graphData?.edges ?? [];

  const WIDTH = 600;
  const HEIGHT = 400;
  const TOP_EDGES = 25;

  // Limit to top edges by weight to avoid hairball with many menu items
  const visibleEdges = useMemo(
    () => [...edges].sort((a, b) => b.weight - a.weight).slice(0, TOP_EDGES),
    [edges],
  );
  const visibleNodeIds = useMemo(() => {
    const ids = new Set<string>();
    for (const e of visibleEdges) { ids.add(e.source); ids.add(e.target); }
    return ids;
  }, [visibleEdges]);
  const visibleNodes = useMemo(
    () => (visibleNodeIds.size > 0 ? nodes.filter((n) => visibleNodeIds.has(n.id)) : nodes.slice(0, 30)),
    [nodes, visibleNodeIds],
  );

  const positioned = useMemo(() => runForceLayout(visibleNodes, visibleEdges, WIDTH, HEIGHT), [visibleNodes, visibleEdges]);
  const nodeMap = useMemo(() => new Map(positioned.map((n) => [n.id, n])), [positioned]);
  const maxWeight = useMemo(() => Math.max(...visibleEdges.map((e) => e.weight), 1), [visibleEdges]);

  const handleMouseEnter = useCallback(
    (node: PositionedNode, event: React.MouseEvent<SVGCircleElement>) => {
      const rect = (event.target as SVGCircleElement).getBoundingClientRect();
      setTooltip({ node, x: rect.left + rect.width / 2, y: rect.top - 8 });
    },
    [],
  );

  const handleMouseLeave = useCallback(() => setTooltip(null), []);

  if (!nodes.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-muted-foreground">No network data available</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md"
          style={{ left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)" }}
        >
          <p className="font-semibold text-slate-800">{tooltip.node.label}</p>
          <p className="text-slate-500">
            Value: <span className="font-mono tabular-nums">{tooltip.node.value.toLocaleString("en-IN")}</span>
          </p>
        </div>
      )}

      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full" preserveAspectRatio="xMidYMid meet">
        {/* Edges — filtered to top 25 by weight */}
        {visibleEdges.map((edge, i) => {
          const source = nodeMap.get(edge.source);
          const target = nodeMap.get(edge.target);
          if (!source || !target) return null;
          const thickness = Math.max(1, (edge.weight / maxWeight) * 5);
          return (
            <line
              key={`edge-${i}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="#cbd5e1"
              strokeWidth={thickness}
              strokeOpacity={0.6}
            />
          );
        })}

        {/* Nodes */}
        {positioned.map((node, i) => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={node.radius}
              fill={getChartColor(i)}
              fillOpacity={0.85}
              stroke="#fff"
              strokeWidth={2}
              className="cursor-pointer transition-opacity hover:opacity-100"
              opacity={0.85}
              onMouseEnter={(e) => handleMouseEnter(node, e)}
              onMouseLeave={handleMouseLeave}
            />
            {/* Always show labels for nodes above a minimum size */}
            {node.radius >= 12 && (
              <text
                x={node.x}
                y={node.y + node.radius + 14}
                textAnchor="middle"
                fontSize={10}
                fill="#475569"
                fontWeight={500}
              >
                {node.label.length > 14 ? node.label.slice(0, 13) + "..." : node.label}
              </text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}
