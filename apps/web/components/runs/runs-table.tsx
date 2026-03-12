"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { api, JobRead } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const PAGE_SIZE = 12;

const columns: ColumnDef<JobRead>[] = [
  { accessorKey: "id", header: "Job ID" },
  { accessorKey: "kind", header: "Kind" },
  { accessorKey: "status", header: "Status" },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
  },
];

export function RunsTable() {
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);

  const [statusFilter, setStatusFilter] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [offset, setOffset] = useState(0);

  const jobsQuery = useQuery({
    queryKey: [
      ...queryKeys.jobs.list(workspaceId || "none", projectId || "none"),
      statusFilter || "all",
      kindFilter || "all",
      offset,
      PAGE_SIZE,
    ],
    queryFn: () =>
      api.listJobsPage({
        workspaceId,
        projectId,
        status: statusFilter || undefined,
        kind: kindFilter || undefined,
        offset,
        limit: PAGE_SIZE,
      }),
    enabled: authToken.trim().length > 0 && workspaceId.trim().length > 0,
  });

  const usageQuery = useQuery({
    queryKey: queryKeys.usage.summary(workspaceId || "none", projectId || "none"),
    queryFn: () => api.getUsageSummary(workspaceId, projectId),
    enabled: authToken.trim().length > 0 && workspaceId.trim().length > 0,
  });

  const rows = useMemo(() => jobsQuery.data ?? [], [jobsQuery.data]);

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!authToken.trim()) {
    return <div className="text-sm text-muted-foreground">Sign in to view runs.</div>;
  }

  if (!workspaceId) {
    return <div className="text-sm text-muted-foreground">Select a workspace to view runs.</div>;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Requests</CardDescription>
            <CardTitle className="text-lg">{usageQuery.data?.request_count ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Tokens</CardDescription>
            <CardTitle className="text-lg">{usageQuery.data?.total_tokens ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Prompt Tokens</CardDescription>
            <CardTitle className="text-lg">{usageQuery.data?.prompt_tokens ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Estimated Cost</CardDescription>
            <CardTitle className="text-lg">${(usageQuery.data?.estimated_cost_usd ?? 0).toFixed(4)}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Jobs</CardTitle>
          <CardDescription>Server-filtered and paginated run jobs.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 md:grid-cols-[200px_220px_auto]">
            <Select
              value={statusFilter}
              onChange={(event) => {
                setOffset(0);
                setStatusFilter(event.target.value);
              }}
            >
              <option value="">All statuses</option>
              <option value="queued">queued</option>
              <option value="running">running</option>
              <option value="retry">retry</option>
              <option value="completed">completed</option>
              <option value="failed">failed</option>
            </Select>
            <Input
              placeholder="Filter by kind"
              value={kindFilter}
              onChange={(event) => {
                setOffset(0);
                setKindFilter(event.target.value);
              }}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOffset((prev) => Math.max(prev - PAGE_SIZE, 0))} disabled={offset === 0}>
                Previous
              </Button>
              <Button
                variant="outline"
                onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
                disabled={(jobsQuery.data?.length ?? 0) < PAGE_SIZE}
              >
                Next
              </Button>
            </div>
          </div>

          {jobsQuery.isLoading ? <p className="text-sm text-muted-foreground">Loading jobs...</p> : null}
          {jobsQuery.isError ? <p className="text-sm text-destructive">Failed to load jobs.</p> : null}
          {!jobsQuery.isLoading && !jobsQuery.isError ? (
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
                {table.getRowModel().rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground">
                      No jobs found.
                    </TableCell>
                  </TableRow>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id}>
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
