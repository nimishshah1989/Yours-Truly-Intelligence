"use client";

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { AlertRule } from "@/lib/types";

const SCHEDULE_CONFIG: Record<string, { label: string; className: string }> = {
  daily: { label: "Daily", className: "bg-teal-50 text-teal-700 border-teal-200" },
  weekly: { label: "Weekly", className: "bg-blue-50 text-blue-700 border-blue-200" },
  monthly: { label: "Monthly", className: "bg-violet-50 text-violet-700 border-violet-200" },
};

interface AlertRuleCardProps {
  rule: AlertRule;
  onMutate: () => void;
}

export function AlertRuleCard({ rule, onMutate }: AlertRuleCardProps) {
  const [toggling, setToggling] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const scheduleCfg =
    SCHEDULE_CONFIG[rule.schedule] ?? { label: rule.schedule, className: "bg-slate-100 text-slate-600 border-slate-300" };

  async function handleToggle() {
    setToggling(true);
    try {
      await api.patch(`/api/alerts/rules/${rule.id}`, { is_active: !rule.is_active });
      onMutate();
    } finally {
      setToggling(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete alert rule "${rule.name}"?`)) return;
    setDeleting(true);
    try {
      await api.delete(`/api/alerts/rules/${rule.id}`);
      onMutate();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Card className={cn(
      "rounded-xl border-slate-200 bg-white transition-opacity",
      !rule.is_active && "opacity-60"
    )}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-slate-900 text-sm">{rule.name}</span>
              <Badge variant="outline" className={cn("text-xs", scheduleCfg.className)}>
                {scheduleCfg.label}
              </Badge>
            </div>
            {rule.description && (
              <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                {rule.description}
              </p>
            )}
            <p className="mt-1 text-xs text-muted-foreground font-mono tabular-nums">
              Created {new Date(rule.created_at).toLocaleDateString("en-IN")}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Switch
              checked={rule.is_active}
              disabled={toggling}
              onCheckedChange={handleToggle}
              aria-label={rule.is_active ? "Disable rule" : "Enable rule"}
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-slate-400 hover:text-slate-700"
              disabled={deleting}
              onClick={handleDelete}
              aria-label="Delete rule"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
