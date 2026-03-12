"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { TOOLTIP_STYLE, AXIS_STYLE, GRID_STYLE, getChartColor } from "@/lib/chart-config";
import { formatPriceCompact, formatDateShort } from "@/lib/utils";

/** Format x-axis tick: try date parse first, fall back to raw string */
function smartFormatX(v: string): string {
  if (!v) return "";
  const d = new Date(v);
  return isNaN(d.getTime()) ? String(v) : formatDateShort(v);
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LineConfig {
  key: string;
  name: string;
  color?: string;
}

interface LineChartConfig {
  xKey?: string;
  lines?: LineConfig[];
  currency?: boolean;
  yLabel?: string;
}

interface LineChartWidgetProps {
  data: Record<string, unknown>[];
  config?: LineChartConfig;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive line definitions from the first data row when config.lines is absent */
function inferLines(data: Record<string, unknown>[], xKey: string): LineConfig[] {
  if (data.length === 0) return [];
  return Object.keys(data[0])
    .filter((k) => k !== xKey && typeof data[0][k] === "number")
    .map((k) => ({ key: k, name: k }));
}

function formatYTick(value: number, currency: boolean): string {
  if (currency) return formatPriceCompact(value);
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return String(value);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LineChartWidget({ data, config }: LineChartWidgetProps) {
  const xKey = config?.xKey ?? "date";
  const currency = config?.currency ?? false;
  const lines = config?.lines ?? inferLines(data, xKey);

  if (!data.length || lines.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-muted-foreground">No data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 4, bottom: 0 }}>
        <CartesianGrid {...GRID_STYLE} />
        <XAxis
          dataKey={xKey}
          {...AXIS_STYLE}
          tickFormatter={(v: string) => smartFormatX(v)}
          tickMargin={8}
        />
        <YAxis
          {...AXIS_STYLE}
          tickFormatter={(v: number) => formatYTick(v, currency)}
          label={
            config?.yLabel
              ? { value: config.yLabel, angle: -90, position: "insideLeft", style: { fontSize: 12, fill: "#64748b" } }
              : undefined
          }
          width={60}
        />
        <Tooltip
          {...TOOLTIP_STYLE}
          formatter={(value: number | undefined, name: string | undefined) => {
            const v = value ?? 0;
            const display = currency ? formatPriceCompact(v) : v.toLocaleString("en-IN");
            return [display, name ?? ""];
          }}
          labelFormatter={(label) => smartFormatX(String(label))}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        {lines.map((line, idx) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name}
            stroke={line.color ?? getChartColor(idx)}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
