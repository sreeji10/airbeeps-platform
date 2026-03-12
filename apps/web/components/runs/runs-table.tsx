"use client";

import { ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type RunRow = {
  id: string;
  agent: string;
  status: "completed" | "running" | "failed";
  createdAt: string;
};

const data: RunRow[] = [
  { id: "run_2391", agent: "Support Copilot", status: "completed", createdAt: "2026-03-11 10:03" },
  { id: "run_2392", agent: "Knowledge Synth", status: "running", createdAt: "2026-03-11 10:07" },
  { id: "run_2393", agent: "Ops Analyst", status: "failed", createdAt: "2026-03-11 10:09" },
];

const columns: ColumnDef<RunRow>[] = [
  { accessorKey: "id", header: "Run ID" },
  { accessorKey: "agent", header: "Agent" },
  { accessorKey: "status", header: "Status" },
  { accessorKey: "createdAt", header: "Created" },
];

export function RunsTable() {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Runs</CardTitle>
        <CardDescription>Initial TanStack Table integration for run visibility.</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
