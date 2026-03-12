"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import { CHART_COLOR, SEMANTIC_COLORS } from "@/lib/constants";
import { AXIS_STYLE, GRID_STYLE } from "@/lib/chart-config";
import { formatPriceCompact, formatPrice } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WaterfallRow {
  name: string;
  value: number;
  type: "increase" | "decrease" | "total";
}

interface WaterfallConfig {
  nameKey?: string;
  currency?: boolean;
}

interface WaterfallChartWidgetProps {
  data: Record<string, unknown>[];
  config?: WaterfallConfig;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const WATERFALL_COLORS: Record<string, string> = {
  increase: SEMANTIC_COLORS.positive,  // emerald-600
  decrease: SEMANTIC_COLORS.negative,  // red-600
  total: CHART_COLOR.teal,             // teal-500
};

function formatTick(value: number, currency: boolean): string {
  if (currency) return formatPriceCompact(value);
  if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return String(value);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function WaterfallChartWidget({ data, config }: WaterfallChartWidgetProps) {
  const currency = config?.currency ?? false;

  // Build waterfall segments: invisible base + visible bar
  const chartData = useMemo(() => {
    if (!data.length) return [];

    const rows = data as unknown as WaterfallRow[];
    let runningTotal = 0;

    return rows.map((row) => {
      const absValue = Math.abs(row.value);

      if (row.type === "total") {
        const entry = {
          name: row.name,
          _base: 0,
          _bar: row.value,
          _actual: row.value,
          _type: row.type,
        };
        runningTotal = row.value;
        return entry;
      }

      if (row.type === "increase") {
        const base = runningTotal;
        runningTotal += absValue;
        return {
          name: row.name,
          _base: base,
          _bar: absValue,
          _actual: row.value,
          _type: row.type,
        };
      }

      // decrease
      runningTotal -= absValue;
      return {
        name: row.name,
        _base: runningTotal,
        _bar: absValue,
        _actual: row.value,
        _type: row.type,
      };
    });
  }, [data]);

  if (!chartData.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-slate-500">No data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart
        data={chartData}
        margin={{ top: 8, right: 16, left: 4, bottom: 40 }}
      >
        <CartesianGrid {...GRID_STYLE} vertical={false} />

        <XAxis
          dataKey="name"
          {...AXIS_STYLE}
          tickMargin={8}
          angle={-45}
          textAnchor="end"
          height={60}
          interval={0}
          tick={{ fontSize: 11, fill: "#64748b" }}
        />

        <YAxis
          {...AXIS_STYLE}
          tickFormatter={(v: number) => formatTick(v, currency)}
          width={65}
        />

        {/* Custom tooltip that hides the invisible base bar */}
        <Tooltip
          content={({ payload, label }) => {
            if (!payload?.length) return null;
            const entry = payload.find((p) => p.dataKey === "_bar");
            if (!entry) return null;
            const row = entry.payload as { _actual: number; _type: string };
            const display = currency
              ? formatPrice(row._actual)
              : row._actual.toLocaleString("en-IN");
            const typeLabel = row._type === "total" ? "Total" : "Change";
            return (
              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                <p className="text-xs text-slate-500">{label}</p>
                <p className="font-mono text-sm font-semibold tabular-nums text-slate-800">
                  {typeLabel}: {display}
                </p>
              </div>
            );
          }}
        />

        {/* Invisible base bar */}
        <Bar dataKey="_base" stackId="waterfall" fill="transparent" maxBarSize={48} />

        {/* Visible segment */}
        <Bar dataKey="_bar" stackId="waterfall" radius={[4, 4, 0, 0]} maxBarSize={48}>
          {chartData.map((entry) => (
            <Cell
              key={entry.name}
              fill={WATERFALL_COLORS[entry._type] ?? CHART_COLOR.teal}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
