"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  ReferenceLine,
  Label,
} from "recharts";
import type { ScatterShapeProps } from "recharts";
import { AXIS_STYLE, GRID_STYLE, getChartColor } from "@/lib/chart-config";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QuadrantConfig {
  xKey?: string;
  yKey?: string;
  nameKey?: string;
  sizeKey?: string;
  xLabel?: string;
  yLabel?: string;
  quadrantLabels?: {
    topLeft?: string;
    topRight?: string;
    bottomLeft?: string;
    bottomRight?: string;
  };
}

interface QuadrantChartProps {
  data: Record<string, unknown>[];
  config?: QuadrantConfig;
}

interface ScatterPoint {
  x: number;
  y: number;
  z: number;
  name: string;
  _index: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function computeMedian(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------

interface PayloadEntry {
  payload?: ScatterPoint;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: PayloadEntry[];
  xLabel: string;
  yLabel: string;
}

function QuadrantTooltip({ active, payload, xLabel, yLabel }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  if (!point) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-semibold text-slate-800">{point.name}</p>
      <p className="text-slate-600">
        {xLabel}: <span className="font-mono tabular-nums">{point.x.toLocaleString("en-IN")}</span>
      </p>
      <p className="text-slate-600">
        {yLabel}: <span className="font-mono tabular-nums">{point.y.toLocaleString("en-IN")}</span>
      </p>
      {point.z > 0 && (
        <p className="text-slate-600">
          Size: <span className="font-mono tabular-nums">{point.z.toLocaleString("en-IN")}</span>
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Custom scatter shape -- renders labeled bubble per point
// ---------------------------------------------------------------------------

function renderScatterPoint(
  props: ScatterShapeProps,
  hasSizeKey: boolean,
): React.ReactElement | null {
  const { cx, cy } = props;
  const payload = props.payload as ScatterPoint | undefined;
  if (cx == null || cy == null || !payload) return null;
  const idx = payload._index ?? 0;
  const radius = hasSizeKey ? Math.sqrt(payload.z) * 2 + 4 : 6;
  const trimmedName = payload.name.length > 12 ? payload.name.slice(0, 11) + "..." : payload.name;
  return (
    <g>
      <circle cx={cx} cy={cy} r={radius} fill={getChartColor(idx % 6)} stroke="#fff" strokeWidth={1.5} fillOpacity={0.85} />
      <text x={cx} y={cy - radius - 4} textAnchor="middle" fontSize={10} fill="#334155" fontWeight={500}>
        {trimmedName}
      </text>
    </g>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function QuadrantChartWidget({ data, config }: QuadrantChartProps) {
  const xKey = config?.xKey ?? "x";
  const yKey = config?.yKey ?? "y";
  const nameKey = config?.nameKey ?? "name";
  const sizeKey = config?.sizeKey;
  const xLabel = config?.xLabel ?? "Popularity";
  const yLabel = config?.yLabel ?? "Profitability";
  const labels = config?.quadrantLabels ?? {};
  const topRight = labels.topRight ?? "Stars";
  const topLeft = labels.topLeft ?? "Puzzles";
  const bottomRight = labels.bottomRight ?? "Plowhorses";
  const bottomLeft = labels.bottomLeft ?? "Dogs";

  // Transform data into scatter points
  const { points, medianX, medianY, xMax, yMax } = useMemo(() => {
    const pts: ScatterPoint[] = data.map((d, i) => ({
      x: Number(d[xKey]) || 0,
      y: Number(d[yKey]) || 0,
      z: sizeKey ? Number(d[sizeKey]) || 1 : 1,
      name: String(d[nameKey] ?? `Item ${i + 1}`),
      _index: i,
    }));
    const xVals = pts.map((p) => p.x);
    const yVals = pts.map((p) => p.y);
    const mx = computeMedian(xVals);
    const my = computeMedian(yVals);
    const xM = Math.max(...xVals, mx * 1.2) * 1.1;
    const yM = Math.max(...yVals, my * 1.2) * 1.1;
    return { points: pts, medianX: mx, medianY: my, xMax: xM, yMax: yM };
  }, [data, xKey, yKey, nameKey, sizeKey]);

  const hasSizeKey = !!sizeKey;

  if (!data.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-muted-foreground">No data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={380}>
      <ScatterChart margin={{ top: 20, right: 20, left: 8, bottom: 8 }}>
        <CartesianGrid {...GRID_STYLE} />

        {/* Quadrant backgrounds */}
        <ReferenceArea x1={0} x2={medianX} y1={medianY} y2={yMax} fill="#fef3c7" fillOpacity={0.4} />
        <ReferenceArea x1={medianX} x2={xMax} y1={medianY} y2={yMax} fill="#d1fae5" fillOpacity={0.4} />
        <ReferenceArea x1={0} x2={medianX} y1={0} y2={medianY} fill="#fee2e2" fillOpacity={0.4} />
        <ReferenceArea x1={medianX} x2={xMax} y1={0} y2={medianY} fill="#dbeafe" fillOpacity={0.4} />

        {/* Quadrant labels */}
        <ReferenceArea x1={0} x2={medianX * 0.5} y1={yMax * 0.92} y2={yMax}>
          <Label value={topLeft} position="center" style={{ fontSize: 11, fill: "#92400e", fontWeight: 600 }} />
        </ReferenceArea>
        <ReferenceArea x1={medianX * 1.2} x2={xMax} y1={yMax * 0.92} y2={yMax}>
          <Label value={topRight} position="center" style={{ fontSize: 11, fill: "#065f46", fontWeight: 600 }} />
        </ReferenceArea>
        <ReferenceArea x1={0} x2={medianX * 0.5} y1={0} y2={yMax * 0.08}>
          <Label value={bottomLeft} position="center" style={{ fontSize: 11, fill: "#991b1b", fontWeight: 600 }} />
        </ReferenceArea>
        <ReferenceArea x1={medianX * 1.2} x2={xMax} y1={0} y2={yMax * 0.08}>
          <Label value={bottomRight} position="center" style={{ fontSize: 11, fill: "#1e40af", fontWeight: 600 }} />
        </ReferenceArea>

        {/* Median lines */}
        <ReferenceLine x={medianX} stroke="#94a3b8" strokeDasharray="6 4" strokeWidth={1.5} />
        <ReferenceLine y={medianY} stroke="#94a3b8" strokeDasharray="6 4" strokeWidth={1.5} />

        <XAxis type="number" dataKey="x" domain={[0, xMax]} {...AXIS_STYLE} name={xLabel}>
          <Label value={xLabel} offset={-4} position="insideBottom" style={{ fontSize: 12, fill: "#64748b" }} />
        </XAxis>
        <YAxis type="number" dataKey="y" domain={[0, yMax]} {...AXIS_STYLE} width={60} name={yLabel}>
          <Label value={yLabel} angle={-90} position="insideLeft" style={{ fontSize: 12, fill: "#64748b" }} />
        </YAxis>
        {sizeKey && <ZAxis type="number" dataKey="z" range={[40, 400]} />}

        <Tooltip content={<QuadrantTooltip xLabel={xLabel} yLabel={yLabel} />} />

        <Scatter
          data={points}
          fill={getChartColor(0)}
          shape={(props: ScatterShapeProps) => renderScatterPoint(props, hasSizeKey)}
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
