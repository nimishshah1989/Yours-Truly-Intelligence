"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { TOOLTIP_STYLE, AXIS_STYLE, GRID_STYLE, getChartColor } from "@/lib/chart-config";
import { formatPriceCompact } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BarConfig {
  key: string;
  name: string;
  color?: string;
  stackId?: string;
}

interface BarChartConfig {
  xKey?: string;
  bars?: BarConfig[];
  layout?: "vertical" | "horizontal";
  currency?: boolean;
}

interface BarChartWidgetProps {
  data: Record<string, unknown>[];
  config?: BarChartConfig;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive bar definitions from the first data row when config.bars is absent */
function inferBars(data: Record<string, unknown>[], xKey: string): BarConfig[] {
  if (data.length === 0) return [];
  return Object.keys(data[0])
    .filter((k) => k !== xKey && typeof data[0][k] === "number")
    .map((k) => ({ key: k, name: k }));
}

function formatTick(value: number, currency: boolean): string {
  if (currency) return formatPriceCompact(value);
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return String(value);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BarChartWidget({ data, config }: BarChartWidgetProps) {
  const xKey = config?.xKey ?? "name";
  const currency = config?.currency ?? false;
  const isVertical = config?.layout === "vertical";
  const bars = config?.bars ?? inferBars(data, xKey);

  if (!data.length || bars.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-muted-foreground">No data available</p>
      </div>
    );
  }

  // Vertical layout swaps category and value axes
  const categoryAxis = (
    <XAxis
      {...(isVertical ? { type: "number" as const } : {})}
      dataKey={isVertical ? undefined : xKey}
      {...AXIS_STYLE}
      tickMargin={8}
      tickFormatter={isVertical ? (v: number) => formatTick(v, currency) : undefined}
    />
  );

  const valueAxis = (
    <YAxis
      {...(isVertical ? { type: "category" as const, dataKey: xKey, width: 100 } : {})}
      {...AXIS_STYLE}
      tickFormatter={isVertical ? undefined : (v: number) => formatTick(v, currency)}
      width={isVertical ? 100 : 60}
    />
  );

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart
        data={data}
        layout={isVertical ? "vertical" : "horizontal"}
        margin={{ top: 8, right: 16, left: 4, bottom: 0 }}
      >
        <CartesianGrid {...GRID_STYLE} />
        {categoryAxis}
        {valueAxis}
        <Tooltip
          {...TOOLTIP_STYLE}
          formatter={(value: number | undefined, name: string | undefined) => {
            const v = value ?? 0;
            const display = currency ? formatPriceCompact(v) : v.toLocaleString("en-IN");
            return [display, name ?? ""];
          }}
          cursor={{ fill: "rgba(148, 163, 184, 0.1)" }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        {bars.map((bar, idx) => (
          <Bar
            key={bar.key}
            dataKey={bar.key}
            name={bar.name}
            fill={bar.color ?? getChartColor(idx)}
            stackId={bar.stackId}
            radius={bar.stackId ? undefined : [4, 4, 0, 0]}
            maxBarSize={48}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
