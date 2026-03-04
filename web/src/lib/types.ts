// ---------------------------------------------------------------------------
// Core entities
// ---------------------------------------------------------------------------

export interface Restaurant {
  id: number;
  name: string;
  slug: string;
  timezone: string;
  is_active: boolean;
  notification_emails: string | null;
  created_at: string;
}

export interface RestaurantListResponse {
  restaurants: Restaurant[];
  count: number;
}

// ---------------------------------------------------------------------------
// Period
// ---------------------------------------------------------------------------

export type PeriodKey =
  | "today"
  | "yesterday"
  | "7d"
  | "30d"
  | "mtd"
  | "last_month"
  | "custom";

export interface PeriodRange {
  key: PeriodKey;
  start?: string; // ISO date for custom
  end?: string;
}

// ---------------------------------------------------------------------------
// Widget system
// ---------------------------------------------------------------------------

export type WidgetType =
  | "stat_card"
  | "line_chart"
  | "bar_chart"
  | "pie_chart"
  | "heatmap"
  | "quadrant_chart"
  | "waterfall_chart"
  | "table"
  | "network_graph"
  | "gauge"
  | "pareto_chart"
  | "cohort_table"
  | "scatter_plot";

export interface WidgetSpec {
  type: WidgetType;
  title: string;
  subtitle?: string;
  data: Record<string, unknown>[] | Record<string, unknown>;
  config?: Record<string, unknown>;
  span?: 1 | 2 | 3; // grid columns
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

export interface StatCardData {
  label: string;
  value: string;
  change?: number; // percentage change
  changeLabel?: string; // e.g. "vs last week"
  sparkline?: number[];
  prefix?: string;
  suffix?: string;
}

// ---------------------------------------------------------------------------
// Data models (mirrors backend)
// ---------------------------------------------------------------------------

export interface Order {
  id: number;
  restaurant_id: number;
  order_type: string;
  platform: string;
  payment_mode: string;
  status: string;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  platform_commission: number;
  total_amount: number;
  net_amount: number;
  item_count: number;
  table_number: string | null;
  staff_name: string | null;
  is_cancelled: boolean;
  cancel_reason: string | null;
  ordered_at: string;
}

export interface OrderItem {
  id: number;
  order_id: number;
  item_name: string;
  category: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  cost_price: number;
  is_void: boolean;
}

export interface MenuItem {
  id: number;
  name: string;
  category: string;
  sub_category: string | null;
  item_type: string;
  base_price: number;
  cost_price: number;
  is_active: boolean;
}

export interface Customer {
  id: number;
  phone: string | null;
  name: string | null;
  first_visit: string | null;
  last_visit: string | null;
  total_visits: number;
  total_spend: number;
  avg_order_value: number;
  loyalty_tier: string;
}

export interface DailySummary {
  id: number;
  summary_date: string;
  total_revenue: number;
  net_revenue: number;
  total_tax: number;
  total_discounts: number;
  total_commissions: number;
  total_orders: number;
  dine_in_orders: number;
  delivery_orders: number;
  takeaway_orders: number;
  cancelled_orders: number;
  avg_order_value: number;
  unique_customers: number;
  new_customers: number;
  returning_customers: number;
  platform_revenue: Record<string, number>;
  payment_mode_breakdown: Record<string, number>;
}

export interface SavedDashboard {
  id: number;
  title: string;
  description: string | null;
  widget_specs: WidgetSpec[];
  is_pinned: boolean;
  created_at: string;
}

export interface AlertRule {
  id: number;
  name: string;
  description: string | null;
  schedule: string;
  is_active: boolean;
  created_at: string;
}

export interface AlertHistoryEntry {
  id: number;
  alert_rule_id: number;
  triggered_at: string;
  result: Record<string, unknown>;
  was_sent: boolean;
}

export interface ChatSession {
  id: number;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  widgets: WidgetSpec[] | null;
  created_at: string;
}

export interface Digest {
  id: number;
  digest_type: string;
  period_start: string;
  period_end: string;
  content: string;
  widgets: WidgetSpec[] | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// API responses
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  database: string;
  restaurant_count: number;
  order_count: number;
}
