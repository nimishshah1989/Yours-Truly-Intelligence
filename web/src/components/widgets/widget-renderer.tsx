import type { WidgetSpec } from "@/lib/types";
import { StatCard } from "./stat-card";
import { LineChartWidget } from "./line-chart";
import { BarChartWidget } from "./bar-chart";
import { PieChartWidget } from "./pie-chart";
import { HeatmapWidget } from "./heatmap";
import { ParetoChartWidget } from "./pareto-chart";
import { WaterfallChartWidget } from "./waterfall-chart";
import { QuadrantChartWidget } from "./quadrant-chart";
import { TableWidget } from "./table-widget";
import { CohortTableWidget } from "./cohort-table";
import { NetworkGraphWidget } from "./network-graph";
import type { StatCardData } from "@/lib/types";

interface WidgetRendererProps {
  widget: WidgetSpec;
}

export function WidgetRenderer({ widget }: WidgetRendererProps) {
  const arrayData = Array.isArray(widget.data) ? widget.data : [];
  const config = widget.config as Record<string, unknown> | undefined;

  switch (widget.type) {
    case "stat_card":
      return <StatCard data={widget.data as unknown as StatCardData} />;

    case "line_chart":
      return <LineChartWidget data={arrayData} config={config} />;

    case "bar_chart":
      return <BarChartWidget data={arrayData} config={config} />;

    case "pie_chart":
      return <PieChartWidget data={arrayData} config={config} />;

    case "heatmap":
      return <HeatmapWidget data={widget.data as Record<string, unknown>} config={config} />;

    case "pareto_chart":
      return <ParetoChartWidget data={arrayData} config={config} />;

    case "waterfall_chart":
      return <WaterfallChartWidget data={arrayData} config={config} />;

    case "quadrant_chart":
      return <QuadrantChartWidget data={arrayData} config={config} />;

    case "table":
      return <TableWidget data={arrayData} config={config} />;

    case "cohort_table":
      return <CohortTableWidget data={widget.data as Record<string, unknown>} config={config} />;

    case "network_graph":
      return <NetworkGraphWidget data={widget.data as Record<string, unknown>} config={config} />;

    case "gauge":
    case "scatter_plot":
      return (
        <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
          <p className="text-sm text-muted-foreground">
            {widget.type.replace(/_/g, " ")} — coming soon
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
