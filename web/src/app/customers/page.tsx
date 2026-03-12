"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import {
  CustomerStatCards,
  RfmSegmentsChart,
  NewVsReturningTrend,
} from "@/components/customers/customer-stats";
import {
  CohortRetention,
  LtvDistribution,
  CustomerConcentration,
  ChurnRiskTable,
} from "@/components/customers/customer-charts";

// ---------------------------------------------------------------------------
// Page composition
// ---------------------------------------------------------------------------

export default function CustomersPage() {
  return (
    <Suspense>
      <PageHeader
        title="Customer Intelligence"
        description="RFM segmentation, cohort retention, churn prediction, and LTV analysis"
      >
        <PeriodSelector />
      </PageHeader>

      {/* Row 1 — Stat cards */}
      <CustomerStatCards />

      {/* Row 2 — RFM Segments (2/3) + New vs Returning trend (1/3) */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RfmSegmentsChart />
        </div>
        <div>
          <NewVsReturningTrend />
        </div>
      </div>

      {/* Row 3 — Cohort Retention Table (full width) */}
      <div className="mt-6">
        <CohortRetention />
      </div>

      {/* Row 4 — LTV Distribution (1/2) + Concentration Pareto (1/2) */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LtvDistribution />
        <CustomerConcentration />
      </div>

      {/* Row 5 — Churn Risk Table (full width) */}
      <div className="mt-6">
        <ChurnRiskTable />
      </div>
    </Suspense>
  );
}
