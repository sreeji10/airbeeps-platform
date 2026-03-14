"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Bot, Database, MessageSquareText } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAppSettingsStore } from "@/store/app-settings-store";

export function OverviewMetrics() {
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);

  const canLoad = authToken.trim().length > 0 && workspaceId.trim().length > 0 && projectId.trim().length > 0;

  const agentsQuery = useQuery({
    queryKey: queryKeys.agents.list(workspaceId || "none", projectId || "none"),
    queryFn: () => api.listAgents(workspaceId, projectId, false),
    enabled: canLoad,
  });
  const sessionsQuery = useQuery({
    queryKey: queryKeys.chats.sessions(workspaceId || "none", projectId || "none"),
    queryFn: () => api.listChatSessions(workspaceId, projectId),
    enabled: canLoad,
  });
  const datasetsQuery = useQuery({
    queryKey: queryKeys.datasets.list(workspaceId || "none", projectId || "none"),
    queryFn: () => api.listDatasets(workspaceId, projectId),
    enabled: canLoad,
  });
  const jobsQuery = useQuery({
    queryKey: queryKeys.jobs.list(workspaceId || "none", projectId || "none"),
    queryFn: () => api.listJobs(workspaceId, projectId),
    enabled: canLoad,
  });

  const isLoading = canLoad && (agentsQuery.isLoading || sessionsQuery.isLoading || datasetsQuery.isLoading || jobsQuery.isLoading);
  const hasError = agentsQuery.isError || sessionsQuery.isError || datasetsQuery.isError || jobsQuery.isError;

  const jobs = jobsQuery.data ?? [];
  const doneCount = jobs.filter((job) => job.status === "completed").length;
  const failedCount = jobs.filter((job) => job.status === "failed").length;
  const successRate = doneCount + failedCount > 0 ? ((doneCount / (doneCount + failedCount)) * 100).toFixed(1) : "0.0";

  const metrics = [
    { label: "Active Agents", value: String(agentsQuery.data?.length ?? 0), icon: Bot, hint: "active agents in project" },
    {
      label: "Chat Sessions",
      value: String(sessionsQuery.data?.sessions.length ?? 0),
      icon: MessageSquareText,
      hint: "saved chat sessions",
    },
    { label: "Knowledge Sources", value: String(datasetsQuery.data?.length ?? 0), icon: Database, hint: "datasets in project" },
    { label: "Runtime Success", value: `${successRate}%`, icon: Activity, hint: `${doneCount} completed / ${failedCount} failed` },
  ];

  if (!authToken.trim()) {
    return <p className="text-sm text-muted-foreground">Sign in to load workspace metrics.</p>;
  }

  if (!workspaceId || !projectId) {
    return <p className="text-sm text-muted-foreground">Select a workspace and project to load metrics.</p>;
  }

  return (
    <section className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.label}>
              <CardHeader className="flex flex-row items-start justify-between space-y-0">
                <div>
                  <CardDescription>{metric.label}</CardDescription>
                  <CardTitle className="mt-2 text-2xl">{isLoading ? "..." : metric.value}</CardTitle>
                </div>
                <div className="rounded-md bg-secondary p-2 text-secondary-foreground">
                  <Icon className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">{metric.hint}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
      {hasError ? <p className="text-sm text-destructive">Some dashboard metrics failed to load.</p> : null}
    </section>
  );
}
