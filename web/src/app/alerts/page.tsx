"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AlertRuleCard } from "@/components/alerts/alert-rule-card";
import { CreateRuleDialog } from "@/components/alerts/create-rule-dialog";
import { useAlertRules, useAlertHistory } from "@/hooks/use-alerts";
import { formatDate } from "@/lib/utils";
import type { AlertHistoryEntry } from "@/lib/types";

// ---------------------------------------------------------------------------
// Skeleton loaders
// ---------------------------------------------------------------------------

function RulesSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i} className="rounded-xl border-slate-200">
          <CardContent className="p-5">
            <Skeleton className="h-4 w-48 bg-slate-100" />
            <Skeleton className="mt-2 h-3 w-64 bg-slate-100" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function HistorySkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full bg-slate-100 rounded-lg" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Alert history table
// ---------------------------------------------------------------------------

function AlertHistoryTable({ entries }: { entries: AlertHistoryEntry[] }) {
  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-sm font-medium text-slate-700">No alert history yet</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Alerts will appear here once rules have been triggered.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Triggered At
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Rule ID
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Result Preview
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Sent
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {entries.map((entry) => {
            const resultPreview = entry.result
              ? Object.entries(entry.result)
                  .slice(0, 2)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")
              : "—";
            return (
              <tr key={entry.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 font-mono tabular-nums text-slate-700 whitespace-nowrap">
                  {formatDate(entry.triggered_at)}
                </td>
                <td className="px-4 py-3 text-slate-600 font-mono tabular-nums">
                  #{entry.alert_rule_id}
                </td>
                <td className="px-4 py-3 text-slate-600 text-xs max-w-xs truncate">
                  {resultPreview}
                </td>
                <td className="px-4 py-3 text-center">
                  {entry.was_sent ? (
                    <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-xs">
                      Sent
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-slate-100 text-slate-500 border-slate-200 text-xs">
                      Not Sent
                    </Badge>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AlertsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const { data: rules, isLoading: rulesLoading, mutate: mutateRules } = useAlertRules();
  const { data: history, isLoading: historyLoading } = useAlertHistory();

  return (
    <>
      <PageHeader
        title="Alerts & Intelligence"
        description="Automated alert rules for revenue, leakage, and operational anomalies"
      >
        <Button
          className="bg-teal-600 hover:bg-teal-700 text-white"
          onClick={() => setShowCreate(true)}
        >
          <Plus className="h-4 w-4 mr-1.5" />
          Create Alert Rule
        </Button>
      </PageHeader>

      <Tabs defaultValue="rules">
        <TabsList className="mb-6 bg-slate-100">
          <TabsTrigger value="rules" className="data-[state=active]:bg-white data-[state=active]:text-teal-700">
            Alert Rules
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-white data-[state=active]:text-teal-700">
            Alert History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="rules">
          {rulesLoading || !rules ? (
            <RulesSkeleton />
          ) : rules.length === 0 ? (
            <Card className="rounded-xl border-dashed border-slate-300">
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <p className="text-sm font-medium text-slate-700">No alert rules configured</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Create your first alert rule to start monitoring key metrics automatically.
                </p>
                <Button
                  className="mt-4 bg-teal-600 hover:bg-teal-700 text-white"
                  onClick={() => setShowCreate(true)}
                >
                  <Plus className="h-4 w-4 mr-1.5" />
                  Create Alert Rule
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {rules.map((rule) => (
                <AlertRuleCard key={rule.id} rule={rule} onMutate={mutateRules} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="history">
          <Card className="rounded-xl border-slate-200 bg-white">
            <CardContent className="p-5">
              {historyLoading || !history ? (
                <HistorySkeleton />
              ) : (
                <AlertHistoryTable entries={history} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <CreateRuleDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={mutateRules}
      />
    </>
  );
}
