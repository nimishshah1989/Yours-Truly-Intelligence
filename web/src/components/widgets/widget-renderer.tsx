import type { WidgetSpec } from "@/lib/types";
import { StatCard } from "./stat-card";
import type { StatCardData } from "@/lib/types";

interface WidgetRendererProps {
  widget: WidgetSpec;
}

export function WidgetRenderer({ widget }: WidgetRendererProps) {
  switch (widget.type) {
    case "stat_card":
      return <StatCard data={widget.data as unknown as StatCardData} />;

    case "line_chart":
    case "bar_chart":
    case "pie_chart":
    case "heatmap":
    case "quadrant_chart":
    case "waterfall_chart":
    case "table":
    case "network_graph":
    case "gauge":
    case "pareto_chart":
    case "cohort_table":
    case "scatter_plot":
      return (
        <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
          <p className="text-sm text-muted-foreground">
            {widget.type.replace(/_/g, " ")} — coming in Phase 2
          </p>
        </div>
      );

    default:
      return (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-600">
            Unknown widget type: {widget.type}
          </p>
        </div>
      );
  }
}
