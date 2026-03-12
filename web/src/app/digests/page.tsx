"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { GenerateDigestDialog } from "@/components/digests/generate-digest-dialog";
import { useDigests } from "@/hooks/use-digests";
import { cn, formatDate } from "@/lib/utils";
import type { Digest } from "@/lib/types";

// ---------------------------------------------------------------------------
// Type filter buttons
// ---------------------------------------------------------------------------

const DIGEST_TYPES = [
  { key: "all", label: "All" },
  { key: "daily", label: "Daily" },
  { key: "weekly", label: "Weekly" },
  { key: "monthly", label: "Monthly" },
] as const;

type DigestTypeFilter = "all" | "daily" | "weekly" | "monthly";

// ---------------------------------------------------------------------------
// Type badge
// ---------------------------------------------------------------------------

const TYPE_CONFIG: Record<string, { label: string; className: string }> = {
  daily: { label: "Daily", className: "bg-teal-50 text-teal-700 border-teal-200" },
  weekly: { label: "Weekly", className: "bg-blue-50 text-blue-700 border-blue-200" },
  monthly: { label: "Monthly", className: "bg-violet-50 text-violet-700 border-violet-200" },
};

function DigestTypeBadge({ type }: { type: string }) {
  const cfg = TYPE_CONFIG[type] ?? { label: type, className: "bg-slate-100 text-slate-600 border-slate-300" };
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", cfg.className)}>
      {cfg.label}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Single digest card
// ---------------------------------------------------------------------------

function DigestCard({ digest, defaultExpanded }: { digest: Digest; defaultExpanded: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <Card className="rounded-xl border-slate-200 bg-white">
      <button
        className="w-full text-left px-5 py-4 flex items-center justify-between gap-4"
        onClick={() => setExpanded((p) => !p)}
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3 flex-wrap min-w-0">
          <DigestTypeBadge type={digest.digest_type} />
          <span className="font-mono tabular-nums text-sm text-slate-700 whitespace-nowrap">
            {formatDate(digest.period_start)}
            {digest.period_start !== digest.period_end
              ? ` — ${formatDate(digest.period_end)}`
              : ""}
          </span>
          <span className="text-xs text-muted-foreground">
            Generated {formatDate(digest.created_at)}
          </span>
        </div>
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-slate-100 px-5 pb-5 pt-4">
          <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
            {digest.content}
          </pre>
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function DigestSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i} className="rounded-xl border-slate-200">
          <CardContent className="p-5">
            <div className="flex items-center gap-3">
              <Skeleton className="h-5 w-16 bg-slate-100 rounded-full" />
              <Skeleton className="h-4 w-40 bg-slate-100" />
              <Skeleton className="h-4 w-24 bg-slate-100" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DigestsPage() {
  const [typeFilter, setTypeFilter] = useState<DigestTypeFilter>("all");
  const [showGenerate, setShowGenerate] = useState(false);
  const { data: digests, isLoading, mutate } = useDigests();

  const filtered =
    !digests
      ? []
      : typeFilter === "all"
        ? digests
        : digests.filter((d) => d.digest_type === typeFilter);

  return (
    <>
      <PageHeader
        title="Digests & Reports"
        description="AI-generated daily, weekly, and monthly performance summaries"
      >
        <Button
          className="bg-teal-600 hover:bg-teal-700 text-white"
          onClick={() => setShowGenerate(true)}
        >
          <Plus className="h-4 w-4 mr-1.5" />
          Generate Digest
        </Button>
      </PageHeader>

      {/* Type filter buttons */}
      <div className="mb-6 flex items-center gap-2">
        {DIGEST_TYPES.map((t) => (
          <button
            key={t.key}
            onClick={() => setTypeFilter(t.key)}
            className={cn(
              "rounded-lg px-4 py-1.5 text-sm font-medium transition-colors border",
              typeFilter === t.key
                ? "bg-teal-600 text-white border-teal-600"
                : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <DigestSkeleton />
      ) : !digests || digests.length === 0 ? (
        <Card className="rounded-xl border-dashed border-slate-300">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm font-medium text-slate-700">No digests yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Generate your first digest to see AI-powered performance summaries.
            </p>
            <Button
              className="mt-4 bg-teal-600 hover:bg-teal-700 text-white"
              onClick={() => setShowGenerate(true)}
            >
              <Plus className="h-4 w-4 mr-1.5" />
              Generate Digest
            </Button>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card className="rounded-xl border-dashed border-slate-300">
          <CardContent className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground">
              No {typeFilter} digests found.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map((digest, idx) => (
            <DigestCard key={digest.id} digest={digest} defaultExpanded={idx === 0} />
          ))}
        </div>
      )}

      <GenerateDigestDialog
        open={showGenerate}
        onClose={() => setShowGenerate(false)}
        onGenerated={mutate}
      />
    </>
  );
}
