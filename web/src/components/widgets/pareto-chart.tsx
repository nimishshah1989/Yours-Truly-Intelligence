"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { CHART_COLOR, SEMANTIC_COLORS } from "@/lib/constants";
import { TOOLTIP_STYLE, AXIS_STYLE, GRID_STYLE } from "@/lib/chart-config";
import { formatPriceCompact } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ParetoConfig {
  nameKey?: string;
  valueKey?: string;
  currency?: boolean;
}

interface ParetoChartWidgetProps {
  data: Record<string, unknown>[];
  config?: ParetoConfig;
}

interface ParetoRow {
  _value: number;
  _cumulativePct: number;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTick(value: number, currency: boolean): string {
  if (currency) return formatPriceCompact(value);
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return String(value);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ParetoChartWidget({ data, config }: ParetoChartWidgetProps) {
  const nameKey = config?.nameKey ?? "name";
  const valueKey = config?.valueKey ?? "value";
  const currency = config?.currency ?? false;

  // Compute cumulative percentage for each row (data assumed pre-sorted desc)
  const chartData = useMemo(() => {
    if (!data.length) return [] as ParetoRow[];
    const total = data.reduce((sum, row) => sum + (Number(row[valueKey]) || 0), 0);
    if (total === 0) return [] as ParetoRow[];

    let cumulative = 0;
    return data.map((row) => {
      const value = Number(row[valueKey]) || 0;
      cumulative += value;
      return {
        ...row,
        _value: value,
        _cumulativePct: Math.round((cumulative / total) * 1000) / 10,
      } as ParetoRow;
    });
  }, [data, valueKey]);

  if (!chartData.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-slate-500">No data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart
        data={chartData}
        margin={{ top: 8, right: 16, left: 4, bottom: 40 }}
      >
        <CartesianGrid {...GRID_STYLE} vertical={false} />

        <XAxis
          dataKey={nameKey}
          {...AXIS_STYLE}
          tickMargin={8}
          angle={-45}
          textAnchor="end"
          height={60}
          interval={0}
          tick={{ fontSize: 11, fill: "#64748b" }}
        />

        {/* Left axis: absolute values */}
        <YAxis
          yAxisId="left"
          {...AXIS_STYLE}
          tickFormatter={(v: number) => formatTick(v, currency)}
          width={65}
        />

        {/* Right axis: cumulative % */}
        <YAxis
          yAxisId="right"
          orientation="right"
          {...AXIS_STYLE}
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          width={50}
        />

        <Tooltip
          {...TOOLTIP_STYLE}
          content={({ payload, label }) => {
            if (!payload?.length) return null;
            const barEntry = payload.find((p) => p.dataKey === "_value");
            const lineEntry = payload.find((p) => p.dataKey === "_cumulativePct");
            const barVal = Number(barEntry?.value ?? 0);
            const lineVal = Number(lineEntry?.value ?? 0);
            const display = currency ? formatPriceCompact(barVal) : barVal.toLocaleString("en-IN");
            return (
              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                <p className="text-xs text-slate-500">{label}</p>
                <p className="font-mono text-sm font-semibold tabular-nums text-slate-800">
                  {display}
                </p>
                <p className="font-mono text-xs tabular-nums text-slate-500">
                  Cumulative: {lineVal.toFixed(1)}%
                </p>
              </div>
            );
          }}
        />

        {/* 80% reference line */}
        <ReferenceLine
          yAxisId="right"
          y={80}
          stroke={SEMANTIC_COLORS.negative}
          strokeDasharray="6 3"
          strokeWidth={1.5}
          label={{
            value: "80%",
            position: "right",
            fill: SEMANTIC_COLORS.negative,
            fontSize: 11,
            fontWeight: 600,
          }}
        />

        {/* Bars */}
        <Bar
          yAxisId="left"
          dataKey="_value"
          name="Value"
          fill={CHART_COLOR.teal}
          radius={[4, 4, 0, 0]}
          maxBarSize={48}
        />

        {/* Cumulative line */}
        <Line
          yAxisId="right"
          dataKey="_cumulativePct"
          name="Cumulative %"
          type="monotone"
          stroke={CHART_COLOR.rose}
          strokeWidth={2}
          dot={{ r: 3, fill: CHART_COLOR.rose }}
          activeDot={{ r: 5 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
