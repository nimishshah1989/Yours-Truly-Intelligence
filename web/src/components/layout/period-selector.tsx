"use client";

import { Suspense } from "react";
import { usePeriod } from "@/hooks/use-period";
import { PERIOD_OPTIONS } from "@/lib/constants";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PeriodKey } from "@/lib/types";

function PeriodSelectorInner() {
  const { period, setPeriod } = usePeriod();

  return (
    <Select
      value={period.key}
      onValueChange={(val) => setPeriod({ key: val as PeriodKey })}
    >
      <SelectTrigger className="w-[160px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {PERIOD_OPTIONS.map((opt) => (
          <SelectItem key={opt.key} value={opt.key}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function PeriodSelector() {
  return (
    <Suspense fallback={<div className="h-9 w-[160px] animate-pulse rounded-md bg-slate-100" />}>
      <PeriodSelectorInner />
    </Suspense>
  );
}
