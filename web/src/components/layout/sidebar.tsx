"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  ChefHat,
  DollarSign,
  AlertTriangle,
  Users,
  Clock,
  MessageSquare,
  LayoutDashboard,
  Bell,
  FileText,
  GitCompareArrows,
  Database,
  Home,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import { RestaurantSelector } from "./restaurant-selector";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

const MAIN_NAV: NavItem[] = [
  { href: "/", label: "Home", icon: Home },
  { href: "/chat", label: "Ask", icon: MessageSquare },
];

const ANALYTICS_NAV: NavItem[] = [
  { href: "/revenue", label: "Revenue Analytics", icon: BarChart3 },
  { href: "/cost", label: "Cost Analytics", icon: DollarSign },
  { href: "/menu", label: "Menu Analytics", icon: ChefHat },
  { href: "/operations", label: "Operations", icon: Clock },
  { href: "/leakage", label: "Leakage & Loss", icon: AlertTriangle },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/reconciliation", label: "Reconciliation", icon: GitCompareArrows },
];

const TOOLS_NAV: NavItem[] = [
  { href: "/briefing", label: "Briefing", icon: FileText },
  { href: "/dashboards", label: "Dashboards", icon: LayoutDashboard },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/digests", label: "Digests", icon: Lightbulb },
  { href: "/data", label: "Data Status", icon: Database },
];

function NavLink({ item, isActive }: { item: NavItem; isActive: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        isActive
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {item.label}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      {/* Brand */}
      <div className="flex h-14 items-center border-b border-slate-200 px-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-xs font-bold text-white">
            YT
          </div>
          <span className="text-sm font-semibold text-foreground">
            YoursTruly
          </span>
        </Link>
      </div>

      {/* Restaurant selector */}
      <div className="px-3 pt-4 pb-2">
        <RestaurantSelector />
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        {/* Main */}
        <div className="space-y-0.5">
          {MAIN_NAV.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              isActive={isActive(item.href)}
            />
          ))}
        </div>

        <Separator className="my-4" />

        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Analytics
        </div>
        <div className="space-y-0.5">
          {ANALYTICS_NAV.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              isActive={isActive(item.href)}
            />
          ))}
        </div>

        <Separator className="my-4" />

        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Tools
        </div>
        <div className="space-y-0.5">
          {TOOLS_NAV.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              isActive={isActive(item.href)}
            />
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-200 px-4 py-3">
        <p className="text-xs text-muted-foreground">
          YTIP v0.1
        </p>
      </div>
    </aside>
  );
}
