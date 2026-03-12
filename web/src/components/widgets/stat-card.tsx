import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import type { StatCardData } from "@/lib/types";

interface StatCardProps {
  data: StatCardData;
}

export function StatCard({ data }: StatCardProps) {
  const { label, value, change, changeLabel } = data;

  const isPositive = change != null && change >= 0;
  const isNegative = change != null && change < 0;

  return (
    <Card className="rounded-xl border-slate-200">
      <CardContent className="p-5">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-2xl font-semibold tabular-nums text-foreground">
            {data.prefix}
            {value}
            {data.suffix}
          </span>
          {change != null && (
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium tabular-nums",
                isPositive && "bg-emerald-50 text-emerald-700",
                isNegative && "bg-red-50 text-red-700"
              )}
            >
              {isPositive ? "+" : ""}
              {change.toFixed(1)}%
            </span>
          )}
        </div>
        {changeLabel && (
          <p className="mt-1 text-xs text-muted-foreground">{changeLabel}</p>
        )}
      </CardContent>
    </Card>
  );
}
