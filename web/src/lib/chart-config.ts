import { CHART_COLORS } from "./constants";

// Default Recharts tooltip style
export const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: "white",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    fontSize: "13px",
    padding: "8px 12px",
    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
  },
  itemStyle: {
    padding: "2px 0",
  },
};

// Get chart color by index (wraps around)
export function getChartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

// Default axis style
export const AXIS_STYLE = {
  tick: { fontSize: 12, fill: "#64748b" },
  axisLine: { stroke: "#e2e8f0" },
  tickLine: { stroke: "#e2e8f0" },
};

// Grid style
export const GRID_STYLE = {
  strokeDasharray: "3 3",
  stroke: "#f1f5f9",
};
