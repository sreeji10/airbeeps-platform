"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const DEMO_WORKSPACE_ID = process.env.NEXT_PUBLIC_DEFAULT_WORKSPACE_ID ?? "workspace-demo";
const DEMO_PROJECT_ID = process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID ?? "project-demo";

export function AgentsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["agents", DEMO_WORKSPACE_ID, DEMO_PROJECT_ID],
    queryFn: () => api.listAgents(DEMO_WORKSPACE_ID, DEMO_PROJECT_ID),
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading agents...</div>;
  }

  if (error) {
    return (
      <div className="text-sm text-destructive">
        Could not load agents. Set auth token in localStorage key `airbeeps_auth_token`.
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
