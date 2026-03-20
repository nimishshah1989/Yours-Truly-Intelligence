"use client";

import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ColumnDef,
} from "@tanstack/react-table";
import { cn, formatPrice, formatIndianNumber } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ColumnConfig {
  key: string;
  label: string;
  format?: "currency" | "percent" | "number" | "text";
}

interface TableConfig {
  columns?: ColumnConfig[];
  sortable?: boolean;
  pageSize?: number;
}

interface TableWidgetProps {
  data: Record<string, unknown>[];
  config?: TableConfig;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type RowData = Record<string, unknown>;

function formatCellValue(value: unknown, format?: string): string {
  if (value === null || value === undefined) return "-";
  switch (format) {
    case "currency":
      return formatPrice(Number(value));
    case "percent":
      return `${Number(value).toFixed(1)}%`;
    case "number":
      return formatIndianNumber(Number(value));
    case "text":
    default:
      return String(value);
  }
}

/** Infer column definitions from data keys when no config is provided */
function inferColumns(data: RowData[]): ColumnConfig[] {
  if (data.length === 0) return [];
  return Object.keys(data[0]).filter((k) => !k.startsWith("_")).map((key) => {
    const sample = data[0][key];
    let format: ColumnConfig["format"] = "text";
    if (typeof sample === "number") format = "number";
    return { key, label: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()), format };
  });
}

function isNumericFormat(format?: string): boolean {
  return format === "currency" || format === "percent" || format === "number";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TableWidget({ data, config }: TableWidgetProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const sortable = config?.sortable ?? true;
  const pageSize = config?.pageSize ?? 50;
  const columnConfigs = useMemo(() => config?.columns ?? inferColumns(data), [config?.columns, data]);

  const columnHelper = createColumnHelper<RowData>();

  const columns = useMemo<ColumnDef<RowData, unknown>[]>(
    () =>
      columnConfigs.map((col) =>
        columnHelper.accessor((row) => row[col.key], {
          id: col.key,
          header: () => col.label,
          cell: (info) => formatCellValue(info.getValue(), col.format),
          enableSorting: sortable,
          meta: { format: col.format },
        }),
      ),
    [columnConfigs, columnHelper, sortable],
  );

  const slicedData = useMemo(() => data.slice(0, pageSize), [data, pageSize]);

  const table = useReactTable({
    data: slicedData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (!data.length) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-muted-foreground">No data available</p>
      </div>
    );
  }

  return (
    <div className="table-scroll-wrapper overflow-auto rounded-lg border border-slate-200">
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 z-10 bg-slate-50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const meta = header.column.columnDef.meta as { format?: string } | undefined;
                const numeric = isNumericFormat(meta?.format);
                return (
                  <th
                    key={header.id}
                    className={cn(
                      "border-b border-slate-200 px-3 py-2.5 text-xs font-semibold text-slate-600",
                      numeric ? "text-right" : "text-left",
                      sortable && "cursor-pointer select-none hover:text-slate-900",
                    )}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <span className="inline-flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {sortable && header.column.getIsSorted() === "asc" && <span className="text-teal-600">&#9650;</span>}
                      {sortable && header.column.getIsSorted() === "desc" && <span className="text-teal-600">&#9660;</span>}
                    </span>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row, rowIdx) => {
            const rowClass = (row.original as Record<string, unknown>)._rowClass as string | undefined;
            return (
            <tr
              key={row.id}
              className={cn(
                "transition-colors hover:bg-slate-50",
                rowIdx % 2 === 0 ? "bg-white" : "bg-slate-50/50",
                rowClass,
              )}
            >
              {row.getVisibleCells().map((cell) => {
                const meta = cell.column.columnDef.meta as { format?: string } | undefined;
                const numeric = isNumericFormat(meta?.format);
                return (
                  <td
                    key={cell.id}
                    className={cn(
                      "border-b border-slate-100 px-3 py-2 text-slate-700",
                      numeric && "text-right font-mono tabular-nums",
                    )}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                );
              })}
            </tr>
            );
          })}
        </tbody>
      </table>
      {data.length > pageSize && (
        <div className="border-t border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
          Showing {pageSize} of {data.length.toLocaleString("en-IN")} rows
        </div>
      )}
    </div>
  );
}
