import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format paisa amount to Indian currency string.
 * 50000000 → "₹5,00,000" (5 lakh)
 * Handles null, undefined, and NaN gracefully.
 */
export function formatPrice(paisa: number | null | undefined): string {
  if (paisa == null || isNaN(paisa)) return "₹0";
  const rupees = paisa / 100;
  return "₹" + formatIndianNumber(rupees);
}

/**
 * Compact price for tight spaces.
 * 50000000 → "₹5.0L", 1000000000 → "₹1.0Cr"
 * Handles null, undefined, and NaN gracefully.
 */
export function formatPriceCompact(paisa: number | null | undefined): string {
  if (paisa == null || isNaN(paisa)) return "₹0";
  const rupees = paisa / 100;
  if (rupees >= 10000000) {
    return `₹${(rupees / 10000000).toFixed(1)}Cr`;
  }
  if (rupees >= 100000) {
    return `₹${(rupees / 100000).toFixed(1)}L`;
  }
  if (rupees >= 1000) {
    return `₹${(rupees / 1000).toFixed(1)}K`;
  }
  return `₹${rupees.toFixed(0)}`;
}

/**
 * Format number with Indian grouping: 1,00,000 not 100,000.
 */
export function formatIndianNumber(num: number): string {
  if (isNaN(num)) return "0";
  const parts = Math.abs(num).toFixed(0).split(".");
  const intPart = parts[0];
  const sign = num < 0 ? "-" : "";

  if (intPart.length <= 3) return sign + intPart;

  const last3 = intPart.slice(-3);
  const rest = intPart.slice(0, -3);
  const grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return sign + grouped + "," + last3;
}

export function formatPercent(value: number | null | undefined, decimals: number = 1): string {
  if (value == null || isNaN(value)) return "+0.0%";
  return `${value >= 0 ? "+" : ""}${value.toFixed(decimals)}%`;
}

export function formatNumber(num: number | null | undefined): string {
  if (num == null || isNaN(num)) return "0";
  return formatIndianNumber(Math.round(num));
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateShort(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}
