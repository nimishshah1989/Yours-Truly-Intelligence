"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

export interface DataGapItem {
  field: string;
  impact: string;
  source: string;
  severity: "high" | "medium" | "low";
}

export interface DataStatusOrderInfo {
  count: number;
  date_from: string | null;
  date_to: string | null;
  status: "ok" | "empty";
}

export interface DataStatusItemInfo {
  count: number;
  unique_items: number;
  categories: number;
  status: "ok" | "empty";
}

export interface DataStatusFieldInfo {
  count: number;
  status: "ok" | "missing" | "not_configured" | "empty";
  reason?: string;
}

export interface TopItem {
  name: string;
  category: string;
  revenue: number;
  quantity: number;
}

export interface TopVendor {
  vendor_name: string;
  invoice_count: number;
  total_amount: number;
}

export interface DataStatusResponse {
  petpooja: {
    orders: DataStatusOrderInfo;
    order_items: DataStatusItemInfo;
    top_items: TopItem[];
    cost_price: DataStatusFieldInfo;
    staff_data: DataStatusFieldInfo;
    modifiers: DataStatusFieldInfo;
    void_records: DataStatusFieldInfo;
    customer_data: DataStatusFieldInfo;
    inventory: DataStatusFieldInfo;
    order_types: Record<string, number>;
    payment_modes: Record<string, number>;
  };
  tally: {
    vouchers: DataStatusOrderInfo;
    food_purchases: {
      count: number;
      total_amount: number;
      vendor_count: number;
      status: "ok" | "empty";
    };
    expense_entries: {
      count: number;
      status: "ok" | "empty";
    };
    top_vendors: TopVendor[];
    expense_summary: {
      food_cost: number;
      labour: number;
      rent_facility: number;
      marketing: number;
      other: number;
    };
    voucher_date_from: string | null;
    voucher_date_to: string | null;
  };
  data_gaps: DataGapItem[];
  data_coverage: Record<string, "full" | "partial" | "limited" | "none">;
  last_order_date: string | null;
  last_tally_date: string | null;
}

export function useDataStatus() {
  return useSWR<DataStatusResponse>(
    "/api/data-status",
    (path: string) => api.get<DataStatusResponse>(path),
    { revalidateOnFocus: false },
  );
}
