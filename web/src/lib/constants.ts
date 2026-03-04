import type { PeriodKey } from "./types";

// Chart color palette — teal, blue, amber, rose, violet, emerald
export const CHART_COLORS = [
  "#14b8a6", // teal-500
  "#3b82f6", // blue-500
  "#f59e0b", // amber-500
  "#f43f5e", // rose-500
  "#8b5cf6", // violet-500
  "#10b981", // emerald-500
] as const;

// Named chart colors for direct access
export const CHART_COLOR = {
  teal: "#14b8a6",
  blue: "#3b82f6",
  amber: "#f59e0b",
  rose: "#f43f5e",
  violet: "#8b5cf6",
  emerald: "#10b981",
} as const;

// Semantic colors
export const SEMANTIC_COLORS = {
  positive: "#059669", // emerald-600
  negative: "#dc2626", // red-600
  warning: "#f59e0b", // amber-500
  neutral: "#64748b", // slate-500
} as const;

// Period options for the period selector
export const PERIOD_OPTIONS: { key: PeriodKey; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "yesterday", label: "Yesterday" },
  { key: "7d", label: "Last 7 Days" },
  { key: "30d", label: "Last 30 Days" },
  { key: "mtd", label: "Month to Date" },
  { key: "last_month", label: "Last Month" },
  { key: "custom", label: "Custom Range" },
];

// Order type display
export const ORDER_TYPE_LABELS: Record<string, string> = {
  dine_in: "Dine In",
  delivery: "Delivery",
  takeaway: "Takeaway",
};

export const ORDER_TYPE_COLORS: Record<string, string> = {
  dine_in: CHART_COLOR.teal,
  delivery: CHART_COLOR.blue,
  takeaway: CHART_COLOR.amber,
};

// Platform display
export const PLATFORM_LABELS: Record<string, string> = {
  direct: "Direct",
  swiggy: "Swiggy",
  zomato: "Zomato",
};

export const PLATFORM_COLORS: Record<string, string> = {
  direct: CHART_COLOR.teal,
  swiggy: "#fc8019", // Swiggy orange
  zomato: "#e23744", // Zomato red
};

// Menu category colors
export const MENU_CATEGORY_COLORS: Record<string, string> = {
  Coffee: CHART_COLOR.teal,
  Specialty: CHART_COLOR.blue,
  Beverages: CHART_COLOR.amber,
  Sandwiches: CHART_COLOR.rose,
  Salads: CHART_COLOR.emerald,
  Pizza: CHART_COLOR.violet,
  Pasta: "#06b6d4", // cyan-500
  Desserts: "#ec4899", // pink-500
  Bakery: "#f97316", // orange-500
  Breakfast: "#eab308", // yellow-500
  Sides: "#64748b", // slate-500
};

// Payment mode labels
export const PAYMENT_MODE_LABELS: Record<string, string> = {
  cash: "Cash",
  card: "Card",
  upi: "UPI",
  online: "Online",
};
