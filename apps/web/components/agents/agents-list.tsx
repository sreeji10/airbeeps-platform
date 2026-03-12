"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppSettingsStore } from "@/store/app-settings-store";

export function AgentsList() {
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.agents.list(workspaceId || "none", projectId || "none"),
    queryFn: () => api.listAgents(workspaceId, projectId),
    enabled: authToken.trim().length > 0 && workspaceId.trim().length > 0 && projectId.trim().length > 0,
  });

  if (!authToken.trim()) {
    return <div className="text-sm text-muted-foreground">Sign in to load agents.</div>;
  }

  if (!workspaceId || !projectId) {
    return <div className="text-sm text-muted-foreground">Select a workspace and project to view agents.</div>;
  }

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading agents...</div>;
  }

  if (error) {
    return (
      <div className="text-sm text-destructive">
        Could not load agents. Check workspace/project context and bearer token in Settings.
      </div>
    );
  }

  if (!data || data.length === 0) {
    return <div className="text-sm text-muted-foreground">No agents yet for this workspace/project.</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {data.map((agent) => (
        <Card key={agent.id}>
          <CardHeader>
            <CardTitle className="text-base">{agent.name}</CardTitle>
            <CardDescription>{agent.description ?? "No description provided."}</CardDescription>
          </CardHeader>
          <CardContent>
            <Badge className="border-primary/20 bg-primary/10 text-primary">{agent.status}</Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
