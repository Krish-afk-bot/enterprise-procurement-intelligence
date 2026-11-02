import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { TableOut } from "@/lib/types";

function cellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

/** A table extracted from a page, with its provenance in the caption. */
export function ExtractedTable({ table, caption }: { table: TableOut; caption: string }) {
  const headers = (table.headers ?? []).map(cellText);
  const rows = (table.rows ?? []).map((row) => (Array.isArray(row) ? row.map(cellText) : [cellText(row)]));

  return (
    <figure className="rounded-lg border">
      <figcaption className="flex flex-wrap items-center gap-2 border-b px-3 py-2 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">{table.caption ?? caption}</span>
        <span>{table.extraction_method}</span>
        {table.complexity_score ? <span>complexity {table.complexity_score}</span> : null}
      </figcaption>
      <Table>
        {headers.length > 0 ? (
          <TableHeader>
            <TableRow>
              {headers.map((header, index) => (
                <TableHead key={index} scope="col">
                  {header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
        ) : null}
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <TableCell key={cellIndex} className="tnum text-xs">
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </figure>
  );
}
