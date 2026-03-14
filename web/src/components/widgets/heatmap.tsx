"use client";

import { useState, useMemo, useCallback } from "react";
import { CHART_COLOR } from "@/lib/constants";
import { cn, formatPrice, formatPriceCompact } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HeatmapCell {
  x: string | number;
  y: string | number;
  value: number;
}

interface HeatmapData {
  cells: HeatmapCell[];
  max_value?: number;
  maxValue?: number;
}

interface HeatmapConfig {
  xLabels?: string[];
  yLabels?: string[];
  valueKey?: string;
  colorScale?: string;
  currency?: boolean;
}

interface HeatmapWidgetProps {
  data: Record<string, unknown>;
  config?: HeatmapConfig;
}

interface TooltipState {
  x: string | number;
  y: string | number;
  value: number;
  posX: number;
  posY: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert hex to RGB array */
function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return [20, 184, 166]; // teal-500 fallback
  return [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)];
}

/** Interpolate white → target color based on ratio 0..1 */
function interpolateColor(ratio: number, hex: string): string {
  const [r, g, b] = hexToRgb(hex);
  const clamped = Math.max(0, Math.min(1, ratio));
  // White (255) → color
  const fr = Math.round(255 - (255 - r) * clamped);
  const fg = Math.round(255 - (255 - g) * clamped);
  const fb = Math.round(255 - (255 - b) * clamped);
  return `rgb(${fr}, ${fg}, ${fb})`;
}

function formatCellValue(value: number, currency: boolean): string {
  if (currency) return formatPrice(value);
  return value.toLocaleString("en-IN");
}

/** Format hour number to readable label: 0 → "12a", 13 → "1p" */
function formatHourLabel(hour: string): string {
  const h = Number(hour);
  if (isNaN(h)) return hour;
  if (h === 0) return "12a";
  if (h < 12) return `${h}a`;
  if (h === 12) return "12p";
  return `${h - 12}p`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function HeatmapWidget({ data, config }: HeatmapWidgetProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const heatData = data as unknown as HeatmapData;
  const cells = heatData?.cells ?? [];
  const color = config?.colorScale ?? CHART_COLOR.teal;
  const currency = config?.currency ?? false;

  // Canonical day ordering for heatmaps
  const DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  // Derive labels from data if not provided, with proper ordering
  const xLabels = useMemo(() => {
    if (config?.xLabels?.length) return config.xLabels;
    const unique = [...new Set(cells.map((c) => String(c.x)))];
    // If values look numeric (hours), sort numerically
    const allNumeric = unique.every((v) => !isNaN(Number(v)));
    if (allNumeric) return unique.sort((a, b) => Number(a) - Number(b));
    return unique;
  }, [cells, config?.xLabels]);

  const yLabels = useMemo(() => {
    if (config?.yLabels?.length) return config.yLabels;
    const unique = [...new Set(cells.map((c) => String(c.y)))];
    // If values are day names, sort by canonical day order
    const isDays = unique.every((v) => DAY_ORDER.includes(v));
    if (isDays) return DAY_ORDER.filter((d) => unique.includes(d));
    return unique;
  }, [cells, config?.yLabels]);

  const maxValue = useMemo(() => {
    // Support both snake_case (backend) and camelCase (legacy)
    const provided = heatData?.max_value ?? heatData?.maxValue;
    if (provided) return provided;
    return Math.max(...cells.map((c) => c.value), 1);
  }, [cells, heatData?.max_value, heatData?.maxValue]);

  // Build lookup map: "x|y" → value
  const cellMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const cell of cells) {
      map.set(`${cell.x}|${cell.y}`, cell.value);
    }
    return map;
  }, [cells]);

  const handleMouseEnter = useCallback(
    (x: string, y: string, value: number, event: React.MouseEvent) => {
      const rect = (event.target as HTMLElement).getBoundingClientRect();
      setTooltip({ x, y, value, posX: rect.left + rect.width / 2, posY: rect.top - 8 });
    },
    [],
  );

  const handleMouseLeave = useCallback(() => setTooltip(null), []);

  if (!cells.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-slate-500">No heatmap data available</p>
      </div>
    );
  }

  return (
    <div className="relative overflow-auto">
      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm"
          style={{ left: tooltip.posX, top: tooltip.posY, transform: "translate(-50%, -100%)" }}
        >
          <p className="text-slate-500">
            {tooltip.x} / {tooltip.y}
          </p>
          <p className="font-mono font-semibold tabular-nums text-slate-800">
            {formatCellValue(tooltip.value, currency)}
          </p>
        </div>
      )}

      {/* Grid */}
      <div
        className="grid gap-[2px]"
        style={{
          gridTemplateColumns: `80px repeat(${xLabels.length}, minmax(36px, 1fr))`,
        }}
      >
        {/* Corner spacer */}
        <div />

        {/* Column headers */}
        {xLabels.map((label) => {
          const allNumeric = xLabels.every((v) => !isNaN(Number(v)));
          const displayLabel = allNumeric ? formatHourLabel(label) : label;
          return (
            <div
              key={`col-${label}`}
              className="sticky top-0 z-10 bg-white px-1 py-2 text-center text-xs font-medium text-slate-500 truncate"
            >
              {displayLabel}
            </div>
          );
        })}

        {/* Rows */}
        {yLabels.map((yLabel) => (
          <div key={`row-${yLabel}`} className="contents">
            {/* Row header */}
            <div className="sticky left-0 z-10 flex items-center bg-white pr-2 text-xs font-medium text-slate-500 truncate">
              {yLabel}
            </div>

            {/* Cells */}
            {xLabels.map((xLabel) => {
              const value = cellMap.get(`${xLabel}|${yLabel}`) ?? 0;
              const ratio = maxValue > 0 ? value / maxValue : 0;
              return (
                <div
                  key={`${xLabel}-${yLabel}`}
                  className={cn(
                    "flex items-center justify-center rounded-sm cursor-default transition-opacity",
                    "min-h-[32px] text-xs font-mono tabular-nums",
                    ratio > 0.6 ? "text-white" : "text-slate-700",
                  )}
                  style={{ backgroundColor: interpolateColor(ratio, color) }}
                  onMouseEnter={(e) => handleMouseEnter(xLabel, yLabel, value, e)}
                  onMouseLeave={handleMouseLeave}
                >
                  {value > 0 ? (currency ? formatPriceCompact(value) : value) : ""}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
