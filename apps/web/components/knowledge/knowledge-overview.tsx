"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";

const PAGE_SIZE = 9;

export function KnowledgeOverview() {
  const queryClient = useQueryClient();
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const pushToast = useToastStore((state) => state.push);

  const [statusFilter, setStatusFilter] = useState("");
  const [offset, setOffset] = useState(0);

  const datasetsQuery = useQuery({
    queryKey: [
      ...queryKeys.datasets.list(workspaceId || "none", projectId || "none"),
      statusFilter || "all",
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
      pushToast({ title: "Failed to enqueue ingestion", description: String(error), variant: "error" });
    },
  });

  if (!authToken.trim()) {
    return <div className="text-sm text-muted-foreground">Sign in to view knowledge sources.</div>;
  }

  if (!workspaceId) {
    return <div className="text-sm text-muted-foreground">Select a workspace to view datasets.</div>;
  }

  if (datasetsQuery.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading datasets...</div>;
  }

  if (datasetsQuery.isError) {
    return <div className="text-sm text-destructive">Failed to load datasets.</div>;
  }

  const datasets = datasetsQuery.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <Select
          className="w-56"
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
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setOffset((prev) => Math.max(prev - PAGE_SIZE, 0))} disabled={offset === 0}>
            Previous
          </Button>
          <Button variant="outline" onClick={() => setOffset((prev) => prev + PAGE_SIZE)} disabled={datasets.length < PAGE_SIZE}>
            Next
          </Button>
        </div>
      </div>

      {datasets.length === 0 ? <div className="text-sm text-muted-foreground">No datasets found for current filters.</div> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {datasets.map((dataset) => (
          <Card key={dataset.id}>
            <CardHeader>
              <CardTitle className="text-base">{dataset.name}</CardTitle>
              <CardDescription>Status: {dataset.status}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-xs text-muted-foreground">ID: {dataset.id}</p>
              <p className="text-xs text-muted-foreground">Created: {new Date(dataset.created_at).toLocaleString()}</p>
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => ingestMutation.mutate(dataset.id)}
                disabled={ingestMutation.isPending || !projectId}
              >
                <Play className="mr-2 h-4 w-4" />
                Enqueue Ingestion
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
