"use client";

import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import type { PieLabelRenderProps } from "recharts";
import { TOOLTIP_STYLE, getChartColor } from "@/lib/chart-config";
import { formatPriceCompact } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PieChartConfig {
  nameKey?: string;
  valueKey?: string;
  currency?: boolean;
}

interface PieChartWidgetProps {
  data: Record<string, unknown>[];
  config?: PieChartConfig;
}

// ---------------------------------------------------------------------------
// Custom label rendered on each slice showing percentage
// ---------------------------------------------------------------------------

function renderLabel(props: PieLabelRenderProps) {
  const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props;
  const cxNum = Number(cx ?? 0);
  const cyNum = Number(cy ?? 0);
  const mid = Number(midAngle ?? 0);
  const inner = Number(innerRadius ?? 0);
  const outer = Number(outerRadius ?? 0);
  const pct = Number(percent ?? 0);

  if (pct < 0.04) return null; // skip tiny slices
  const RADIAN = Math.PI / 180;
  const radius = inner + (outer - inner) * 0.55;
  const x = cxNum + radius * Math.cos(-mid * RADIAN);
  const y = cyNum + radius * Math.sin(-mid * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      className="text-xs font-medium"
    >
      {(pct * 100).toFixed(0)}%
    </text>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PieChartWidget({ data, config }: PieChartWidgetProps) {
  const nameKey = config?.nameKey ?? "name";
  const valueKey = config?.valueKey ?? "value";
  const currency = config?.currency ?? false;

  if (!data.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-muted-foreground">No data available</p>
      </div>
    );
  }

  const total = data.reduce((sum, d) => sum + (Number(d[valueKey]) || 0), 0);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={nameKey}
          cx="50%"
          cy="50%"
          outerRadius={105}
          label={renderLabel}
          labelLine={false}
          strokeWidth={2}
          stroke="#fff"
        >
          {data.map((_, idx) => (
            <Cell key={idx} fill={getChartColor(idx)} />
          ))}
        </Pie>
        <Tooltip
          {...TOOLTIP_STYLE}
          formatter={(value: number | undefined, name: string | undefined) => {
            const v = value ?? 0;
            const pct = total > 0 ? ((v / total) * 100).toFixed(1) : "0";
            const display = currency ? formatPriceCompact(v) : v.toLocaleString("en-IN");
            return [`${display} (${pct}%)`, name ?? ""];
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
