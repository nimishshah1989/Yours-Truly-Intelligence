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
  change?: number | null; // percentage change
  changeLabel?: string | null; // e.g. "vs last week"
  sparkline?: number[] | null;
  prefix?: string | null;
  suffix?: string | null;
}

// ---------------------------------------------------------------------------
// Widget data interfaces
// ---------------------------------------------------------------------------

export interface LineChartConfig {
  xKey: string;
  lines: Array<{ key: string; name: string; color?: string }>;
  currency?: boolean;
  yLabel?: string;
}

export interface BarChartConfig {
  xKey: string;
  bars: Array<{ key: string; name: string; color?: string; stackId?: string }>;
  layout?: "vertical" | "horizontal";
  currency?: boolean;
}

export interface PieChartConfig {
  nameKey: string;
  valueKey: string;
  currency?: boolean;
}

export interface HeatmapCell {
  x: string | number;
  y: string | number;
  value: number;
}

export interface HeatmapData {
  cells: HeatmapCell[];
  max_value?: number;
}

export interface HeatmapConfig {
  xLabels?: string[];
  yLabels?: string[];
  valueKey?: string;
  colorScale?: string;
  currency?: boolean;
}

export interface ParetoConfig {
  nameKey: string;
  valueKey: string;
  currency?: boolean;
}

export interface WaterfallRow {
  name: string;
  value: number;
  type: "increase" | "decrease" | "total";
}

export interface QuadrantConfig {
  xKey: string;
  yKey: string;
  nameKey?: string;
  sizeKey?: string;
  xLabel?: string;
  yLabel?: string;
  quadrantLabels?: {
    topLeft: string;
    topRight: string;
    bottomLeft: string;
    bottomRight: string;
  };
}

export interface TableColumn {
  key: string;
  label: string;
  format?: "currency" | "percent" | "number" | "text";
}

export interface TableConfig {
  columns?: TableColumn[];
  sortable?: boolean;
  pageSize?: number;
}

export interface CohortRow {
  label: string;
  size: number;
  retention: number[];
}

export interface CohortData {
  cohorts: CohortRow[];
}

export interface CohortConfig {
  cohortLabel?: string;
  periodLabel?: string;
}

export interface NetworkNode {
  id: string;
  label: string;
  value: number;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
}

export interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

// ---------------------------------------------------------------------------
// API response types — Revenue
// ---------------------------------------------------------------------------

export interface RevenueOverview {
  today_revenue: number;
  today_orders: number;
  avg_ticket: number;
  net_revenue: number;
  wow_change: number | null;
  mom_change: number | null;
  sparkline: number[];
}

export interface TrendPoint {
  date: string;
  revenue: number;
  net_revenue: number;
  orders: number;
}

export interface RevenueHeatmapResponse {
  cells: HeatmapCell[];
  max_value: number;
}

export interface ConcentrationItem {
  name: string;
  revenue: number;
  quantity: number;
  cumulative_pct: number;
}

export interface PaymentModeBreakdown {
  mode: string;
  revenue: number;
  count: number;
}

export interface PaymentModesResponse {
  breakdown: PaymentModeBreakdown[];
  trend: Record<string, unknown>[];
}

export interface PlatformRow {
  platform: string;
  gross: number;
  net: number;
  commission: number;
  discounts: number;
  orders: number;
}

export interface DiscountTrendPoint {
  date: string;
  discounts: number;
  revenue: number;
  rate: number;
}

export interface DiscountAnalysisResponse {
  total_discounts: number;
  discount_rate: number;
  avg_per_order: number;
  discounted_orders: number;
  total_orders: number;
  trend: DiscountTrendPoint[];
}

// ---------------------------------------------------------------------------
// API response types — Menu Engineering
// ---------------------------------------------------------------------------

export interface MenuTopItemRow {
  name: string;
  revenue: number;
  quantity: number;
  category: string;
}

export interface MenuTopItemsResponse {
  by_revenue: MenuTopItemRow[];
  by_quantity: MenuTopItemRow[];
}

export interface MenuBcgItem {
  name: string;
  category: string;
  popularity: number;
  profitability: number;
  revenue: number;
  quadrant: string;
}

export interface MenuBcgResponse {
  items: MenuBcgItem[];
  avg_popularity: number;
  avg_profitability: number;
}

export interface MenuAffinityResponse {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface MenuCannibalizationPair {
  item_a: string;
  item_b: string;
  category: string;
  correlation: number;
}

export interface MenuCannibalizationResponse {
  pairs: MenuCannibalizationPair[];
}

export interface MenuCategoryMixResponse {
  data: Record<string, unknown>[];
  categories: string[];
}

export interface MenuModifierRow {
  item_name: string;
  attach_rate: number;
  revenue_impact: number;
  modifier_count: number;
}

export interface MenuModifierResponse {
  data: MenuModifierRow[];
}

export interface DeadSkuRow {
  name: string;
  category: string;
  last_sold: string | null;
  days_since: number | null;
  total_quantity: number;
}

export interface MenuDeadSkusResponse {
  items: DeadSkuRow[];
}

// ---------------------------------------------------------------------------
// API response types — Cost & Margin
// ---------------------------------------------------------------------------

export interface CogsDayRow {
  date: string;
  cogs: number;
  revenue: number;
  cogs_pct: number;
}

export interface CogsTrendResponse {
  data: CogsDayRow[];
}

export interface VendorPriceCreepResponse {
  items: string[];
  data: Record<string, unknown>[];
}

export interface FoodCostGapRow {
  item_name: string;
  theoretical: number;
  actual: number;
  gap: number;
  gap_pct: number;
}

export interface FoodCostGapResponse {
  data: FoodCostGapRow[];
}

export interface PurchaseCalendarRow {
  date: string;
  total_spend: number;
  vendor_count: number;
  orders: number;
}

export interface PurchaseCalendarResponse {
  data: PurchaseCalendarRow[];
}

export interface WaterfallStep {
  name: string;
  value: number;
  type: string;
}

export interface MarginWaterfallResponse {
  data: WaterfallStep[];
}

export interface VolatilityRow {
  item_name: string;
  min_cost: number;
  max_cost: number;
  avg_cost: number;
  stddev: number;
  volatility_pct: number;
  purchase_count: number;
}

export interface IngredientVolatilityResponse {
  data: VolatilityRow[];
}

// ---------------------------------------------------------------------------
// API response types — Leakage & Loss
// ---------------------------------------------------------------------------

export interface CancellationReasonRow {
  reason: string;
  count: number;
}

export interface CancellationHeatmapResponse {
  cells: HeatmapCell[];
  max_value: number;
  reasons: CancellationReasonRow[];
  total_cancelled: number;
  total_orders: number;
  cancellation_rate: number;
}

export interface VoidStaffRow {
  staff_name: string;
  total_items: number;
  void_items: number;
  void_rate: number;
  is_anomaly: boolean;
  threshold: number;
}

export interface VoidAnomaliesResponse {
  staff: VoidStaffRow[];
  threshold: number;
}

export interface InventoryShrinkageRow {
  item_name: string;
  unit: string;
  theoretical: number;
  actual: number;
  waste: number;
  shrinkage: number;
  shrinkage_pct: number;
}

export interface DiscountAbuseStaffRow {
  staff_name: string;
  total_orders: number;
  discount_count: number;
  frequency: number;
  total_discount: number;
  avg_discount: number;
  is_anomaly: boolean;
}

export interface DiscountAbuseResponse {
  staff: DiscountAbuseStaffRow[];
  frequency_threshold: number;
  amount_threshold: number;
}

export interface PlatformCommissionRow {
  platform: string;
  gross: number;
  net: number;
  commission: number;
  commission_pct: number;
  orders: number;
}

export interface PeakHourRow {
  hour: number;
  actual_revenue: number;
  actual_orders: number;
  potential_revenue: number;
  leakage: number;
  utilization_pct: number;
}

export interface PeakHourLeakageResponse {
  hours: PeakHourRow[];
  peak_capacity: number;
  avg_order_value: number;
  total_leakage: number;
}

// ---------------------------------------------------------------------------
// API response types — Customers
// ---------------------------------------------------------------------------

export interface CustomerTrendPoint {
  date: string;
  new: number;
  returning: number;
}

export interface CustomerOverview {
  total: number;
  new_in_period: number;
  returning: number;
  avg_ltv: number;
  churn_rate: number;
  trend: CustomerTrendPoint[];
}

export interface RfmSegmentSummary {
  name: string;
  count: number;
  avg_spend: number;
  avg_visits: number;
}

export interface RfmCustomerRow {
  name: string;
  phone: string | null;
  segment: string;
  recency: number;
  frequency: number;
  monetary: number;
  last_visit: string;
}

export interface RfmResponse {
  segments: RfmSegmentSummary[];
  customers: RfmCustomerRow[];
}

export interface CohortsResponse {
  cohorts: CohortRow[];
}

export interface ChurnRiskRow {
  name: string;
  phone: string | null;
  total_visits: number;
  total_spend: number;
  last_visit: string;
  avg_interval_days: number;
  days_since: number;
  risk_score: number;
}

export interface LtvBucket {
  bucket: string;
  count: number;
  min_spend: number;
  max_spend: number | null;
}

export interface CustomerConcentrationRow {
  name: string;
  phone: string | null;
  revenue: number;
  orders: number;
  cumulative_pct: number;
}

// ---------------------------------------------------------------------------
// API response types — Operations
// ---------------------------------------------------------------------------

export interface SeatHourResponse {
  cells: HeatmapCell[];
  max_value: number;
}

export interface FulfillmentBucket {
  bucket: string;
  count: number;
  percentage: number;
}

export interface StaffEfficiencyRow {
  staff_name: string;
  orders: number;
  revenue: number;
  avg_ticket: number;
  void_count: number;
  void_rate: number;
}

export interface PlatformSlaRow {
  platform: string;
  total_orders: number;
  on_time: number;
  on_time_pct: number;
  avg_prep_time: number;
}

export interface DaypartRow {
  daypart: string;
  revenue: number;
  cost: number;
  margin: number;
  margin_pct: number;
  orders: number;
  avg_ticket: number;
}

// ---------------------------------------------------------------------------
// API response types — Home
// ---------------------------------------------------------------------------

export interface HomeSummaryResponse {
  stats: StatCardData[];
  last_updated: string;
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
// API response types — Reconciliation
// ---------------------------------------------------------------------------

export type ReconciliationStatus =
  | "matched"
  | "minor_variance"
  | "major_variance"
  | "missing";

export interface ReconciliationSummary {
  total_checks: number;
  matched_count: number;
  minor_variance_count: number;
  major_variance_count: number;
  missing_count: number;
  total_variance_amount: number; // paisa
}

export interface ReconciliationCheck {
  id: number;
  check_date: string;
  check_type: string; // "revenue_match" | "payment_mode_match" | "tax_match" | "data_gap"
  pp_value: number; // paisa
  tally_value: number; // paisa
  variance: number; // paisa
  variance_pct: number;
  status: ReconciliationStatus;
  notes: string | null;
  resolved: boolean;
}

// ---------------------------------------------------------------------------
// API responses — misc
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  database: string;
  restaurant_count: number;
  order_count: number;
}

// ---------------------------------------------------------------------------
// Insight Feed Cards
// ---------------------------------------------------------------------------

export type CardType = "attention" | "opportunity" | "growth" | "optimization";
export type CardPriority = "high" | "medium" | "low";

export interface InsightCard {
  id: number;
  card_type: CardType;
  priority: CardPriority;
  headline: string;
  body: string;
  action_text: string | null;
  action_url: string | null;
  chart_data: Record<string, unknown> | null;
  comparison: string | null;
  is_read: boolean;
  insight_date: string | null;
  created_at: string | null;
}

// ---------------------------------------------------------------------------
// Briefing
// ---------------------------------------------------------------------------

export interface BriefingSection {
  emoji: string;
  title: string;
  body: string;
}

export interface BriefingResponse {
  whatsapp_message: string;
  sections: BriefingSection[];
  anomalies: Array<{
    type: string;
    severity: string;
    message: string;
    value: number;
  }>;
  metrics: Record<string, unknown>;
  target_date: string;
}
