import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/** Skeleton placeholder for a chart card while data is loading. */
export function ChartSkeleton({ height = "h-[340px]" }: { height?: string }) {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <Skeleton className="h-5 w-40 bg-slate-100" />
      </CardHeader>
      <CardContent>
        <Skeleton className={`${height} w-full rounded-lg bg-slate-100`} />
      </CardContent>
    </Card>
  );
}

/** Skeleton placeholder for a stat card while data is loading. */
export function StatSkeleton() {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardContent className="p-5">
        <Skeleton className="h-4 w-28 bg-slate-100" />
        <Skeleton className="mt-3 h-8 w-20 bg-slate-100" />
      </CardContent>
    </Card>
  );
}
