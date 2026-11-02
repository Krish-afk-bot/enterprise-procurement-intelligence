import { ArrowUpDown } from "lucide-react";

import { TableHead } from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type SortKey = "updated" | "title" | "type" | "supplier" | "effective" | "expiry";

export function sortLabel(key: SortKey): string {
  switch (key) {
    case "title":
      return "document name";
    case "type":
      return "type";
    case "supplier":
      return "supplier";
    case "effective":
      return "effective date";
    case "expiry":
      return "expiry date";
    default:
      return "last updated";
  }
}

export function SortableHead({
  label,
  column,
  current,
  ascending,
  onSort,
}: {
  label: string;
  column: SortKey;
  current: SortKey;
  ascending: boolean;
  onSort: (key: SortKey) => void;
}) {
  const active = current === column;
  return (
    <TableHead scope="col" aria-sort={active ? (ascending ? "ascending" : "descending") : "none"}>
      <button
        type="button"
        onClick={() => onSort(column)}
        className={cn(
          "inline-flex items-center gap-1 text-left text-xs font-medium transition-colors duration-micro hover:text-foreground",
          active ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {label}
        <ArrowUpDown className="h-3 w-3" aria-hidden="true" />
      </button>
    </TableHead>
  );
}
