"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Play, RefreshCw } from "lucide-react";

import { api, DatasetRead } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const PAGE_SIZE = 9;

const columns: ColumnDef<DatasetRead>[] = [
  { accessorKey: "name", header: "Dataset" },
  { accessorKey: "status", header: "Status" },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
  },
];

export function KnowledgeOverview() {
  const queryClient = useQueryClient();
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const pushToast = useToastStore((state) => state.push);

  const [statusFilter, setStatusFilter] = useState("");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [offset, setOffset] = useState(0);

  const datasetsQuery = useQuery({
    queryKey: [
      ...queryKeys.datasets.list(workspaceId || "none", projectId || "none"),
      statusFilter || "all",
      sortOrder,
      offset,
      PAGE_SIZE,
    ],
    queryFn: () =>
      api.listDatasetsPage({
        workspaceId,
        projectId,
        status: statusFilter || undefined,
        offset,
        limit: PAGE_SIZE,
        sort: sortOrder,
      }),
    enabled: authToken.trim().length > 0 && workspaceId.trim().length > 0,
  });

  const ingestMutation = useMutation({
    mutationFn: (datasetId: string) => api.enqueueDatasetIngestion(workspaceId, projectId, datasetId),
    onSuccess: () => {
      pushToast({ title: "Ingestion job enqueued" });
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.list(workspaceId, projectId) });
    },
    onError: (error) => {
      pushToast({
        title: "Failed to enqueue ingestion",
        description: error instanceof Error ? error.message : String(error),
        variant: "error",
      });
    },
  });

  const rows = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const hasNextPage = rows.length === PAGE_SIZE;
  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!authToken.trim()) {
    return <div className="text-sm text-muted-foreground">Sign in to view knowledge sources.</div>;
  }

  if (!workspaceId) {
    return <div className="text-sm text-muted-foreground">Select a workspace to view datasets.</div>;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Datasets</CardTitle>
          <CardDescription>Filter, page, and enqueue ingestion jobs from one view.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 md:grid-cols-[220px_160px_auto]">
            <Select
              className="w-full"
              value={statusFilter}
              onChange={(event) => {
                setOffset(0);
                setStatusFilter(event.target.value);
              }}
            >
              <option value="">All statuses</option>
              <option value="pending_ingestion">pending_ingestion</option>
              <option value="ingesting">ingesting</option>
              <option value="ready">ready</option>
              <option value="failed">failed</option>
            </Select>
            <Select
              value={sortOrder}
              onChange={(event) => {
                setOffset(0);
                setSortOrder(event.target.value === "asc" ? "asc" : "desc");
              }}
            >
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </Select>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => void datasetsQuery.refetch()} disabled={datasetsQuery.isFetching}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
              <Button variant="outline" onClick={() => setOffset((prev) => Math.max(prev - PAGE_SIZE, 0))} disabled={offset === 0}>
                Previous
              </Button>
              <Button variant="outline" onClick={() => setOffset((prev) => prev + PAGE_SIZE)} disabled={!hasNextPage}>
                Next
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">Page {page}</p>

          {datasetsQuery.isLoading ? <div className="text-sm text-muted-foreground">Loading datasets...</div> : null}
          {datasetsQuery.isError ? (
            <div className="text-sm text-destructive">
              Failed to load datasets.
              {" "}
              {datasetsQuery.error instanceof Error ? datasetsQuery.error.message : ""}
            </div>
          ) : null}
          {!datasetsQuery.isLoading && !datasetsQuery.isError ? (
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                      </TableHead>
                    ))}
                    <TableHead>Actions</TableHead>
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground">
                      No datasets found for current filters.
                    </TableCell>
                  </TableRow>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id}>
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                      ))}
                      <TableCell>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => ingestMutation.mutate(row.original.id)}
                          disabled={ingestMutation.isPending || !projectId}
                        >
                          <Play className="mr-2 h-4 w-4" />
                          Enqueue Ingestion
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          ) : null}
        </CardContent>
      </Card>
      {!projectId ? (
        <div className="text-xs text-muted-foreground">
          Select a project in the top bar to enable ingestion actions.
        </div>
      ) : null}
    </div>
  );
}
