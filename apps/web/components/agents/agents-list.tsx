"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Edit, Save, Trash2, X } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";

type EditState = {
  agentId: string;
  name: string;
  description: string;
  plannerModel: string;
  generationModel: string;
  fallbackModel: string;
  status: string;
  enabledTools: string;
  datasetIds: string;
  maxToolIterations: string;
} | null;

function splitCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function AgentsList() {
  const queryClient = useQueryClient();
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const pushToast = useToastStore((state) => state.push);
  const [editState, setEditState] = useState<EditState>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.agents.list(workspaceId || "none", projectId || "none"),
    queryFn: () => api.listAgents(workspaceId, projectId, true),
    enabled: authToken.trim().length > 0 && workspaceId.trim().length > 0 && projectId.trim().length > 0,
  });

  const refreshAgents = () => queryClient.invalidateQueries({ queryKey: queryKeys.agents.list(workspaceId, projectId) });

  const updateMutation = useMutation({
    mutationFn: (payload: NonNullable<EditState>) =>
      api.updateAgent(payload.agentId, workspaceId, {
        name: payload.name,
        description: payload.description || undefined,
        planner_model: payload.plannerModel || undefined,
        generation_model: payload.generationModel || undefined,
        fallback_model: payload.fallbackModel || undefined,
        enabled_tools: splitCsv(payload.enabledTools),
        dataset_ids: splitCsv(payload.datasetIds),
        execution_limits: payload.maxToolIterations
          ? {
              max_tool_iterations: Number(payload.maxToolIterations),
            }
          : {},
        status: payload.status,
      }),
    onSuccess: () => {
      pushToast({ title: "Agent updated" });
      setEditState(null);
      void refreshAgents();
    },
    onError: (err) => {
      pushToast({ title: "Update failed", description: String(err), variant: "error" });
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (agentId: string) => api.archiveAgent(agentId, workspaceId),
    onSuccess: () => {
      pushToast({ title: "Agent archived" });
      void refreshAgents();
    },
    onError: (err) => {
      pushToast({ title: "Archive failed", description: String(err), variant: "error" });
    },
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
    return <div className="text-sm text-destructive">Could not load agents.</div>;
  }

  if (!data || data.length === 0) {
    return <div className="text-sm text-muted-foreground">No agents yet for this workspace/project.</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {data.map((agent) => {
        const isEditing = editState?.agentId === agent.id;
        return (
          <Card key={agent.id}>
            <CardHeader>
              {isEditing ? (
                <div className="space-y-3">
                  <div className="space-y-1">
                    <Label>Name</Label>
                    <Input
                      value={editState.name}
                      onChange={(event) =>
                        setEditState((prev) =>
                          prev
                            ? {
                                ...prev,
                                name: event.target.value,
                              }
                            : prev,
                        )
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Description</Label>
                    <Textarea
                      className="min-h-20"
                      value={editState.description}
                      onChange={(event) =>
                        setEditState((prev) =>
                          prev
                            ? {
                                ...prev,
                                description: event.target.value,
                              }
                            : prev,
                        )
                      }
                    />
                  </div>
                  <div className="grid gap-2 md:grid-cols-2">
                    <div className="space-y-1">
                      <Label>Planner Model</Label>
                      <Input
                        value={editState.plannerModel}
                        onChange={(event) =>
                          setEditState((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  plannerModel: event.target.value,
                                }
                              : prev,
                          )
                        }
                      />
                    </div>
                    <div className="space-y-1">
                      <Label>Generation Model</Label>
                      <Input
                        value={editState.generationModel}
                        onChange={(event) =>
                          setEditState((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  generationModel: event.target.value,
                                }
                              : prev,
                          )
                        }
                      />
                    </div>
                  </div>
                  <div className="grid gap-2 md:grid-cols-2">
                    <div className="space-y-1">
                      <Label>Fallback Model</Label>
                      <Input
                        value={editState.fallbackModel}
                        onChange={(event) =>
                          setEditState((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  fallbackModel: event.target.value,
                                }
                              : prev,
                          )
                        }
                      />
                    </div>
                    <div className="space-y-1">
                      <Label>Status</Label>
                      <Select
                        value={editState.status}
                        onChange={(event) =>
                          setEditState((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  status: event.target.value,
                                }
                              : prev,
                          )
                        }
                      >
                        <option value="active">active</option>
                        <option value="paused">paused</option>
                        <option value="archived">archived</option>
                      </Select>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label>Enabled Tools (comma separated)</Label>
                    <Input
                      value={editState.enabledTools}
                      onChange={(event) =>
                        setEditState((prev) =>
                          prev
                            ? {
                                ...prev,
                                enabledTools: event.target.value,
                              }
                            : prev,
                        )
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Dataset IDs (comma separated)</Label>
                    <Input
                      value={editState.datasetIds}
                      onChange={(event) =>
                        setEditState((prev) =>
                          prev
                            ? {
                                ...prev,
                                datasetIds: event.target.value,
                              }
                            : prev,
                        )
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Max Tool Iterations</Label>
                    <Input
                      type="number"
                      value={editState.maxToolIterations}
                      onChange={(event) =>
                        setEditState((prev) =>
                          prev
                            ? {
                                ...prev,
                                maxToolIterations: event.target.value,
                              }
                            : prev,
                        )
                      }
                    />
                  </div>
                </div>
              ) : (
                <>
                  <CardTitle className="text-base">{agent.name}</CardTitle>
                  <CardDescription>{agent.description ?? "No description provided."}</CardDescription>
                </>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {!isEditing ? (
                <div className="space-y-1 text-xs text-muted-foreground">
                  <p>Planner: {agent.planner_model ?? "-"}</p>
                  <p>Generation: {agent.generation_model ?? "-"}</p>
                  <p>Tools: {agent.enabled_tools.length > 0 ? agent.enabled_tools.join(", ") : "-"}</p>
                  <p>Datasets: {agent.dataset_ids.length > 0 ? agent.dataset_ids.join(", ") : "-"}</p>
                </div>
              ) : null}
              <div className="flex items-center gap-2">
                <Badge className="border-primary/20 bg-primary/10 text-primary">{agent.status}</Badge>
                <span className="text-xs text-muted-foreground">{new Date(agent.created_at).toLocaleString()}</span>
              </div>
              <div className="flex gap-2">
                {isEditing ? (
                  <>
                    <Button
                      size="sm"
                      onClick={() => {
                        if (!editState) {
                          return;
                        }
                        updateMutation.mutate(editState);
                      }}
                      disabled={updateMutation.isPending}
                    >
                      <Save className="mr-2 h-4 w-4" />
                      Save
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setEditState(null)}>
                      <X className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                  </>
                ) : (
                  <>
                    <Link
                      href={`/agents/${agent.id}`}
                      className={cn(buttonVariants({ size: "sm", variant: "outline" }))}
                    >
                      Details
                    </Link>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setEditState({
                          agentId: agent.id,
                          name: agent.name,
                          description: agent.description ?? "",
                          plannerModel: agent.planner_model ?? "",
                          generationModel: agent.generation_model ?? "",
                          fallbackModel: agent.fallback_model ?? "",
                          status: agent.status,
                          enabledTools: agent.enabled_tools.join(", "),
                          datasetIds: agent.dataset_ids.join(", "),
                          maxToolIterations: String(
                            typeof agent.execution_limits.max_tool_iterations === "number"
                              ? agent.execution_limits.max_tool_iterations
                              : "",
                          ),
                        })
                      }
                    >
                      <Edit className="mr-2 h-4 w-4" />
                      Edit
                    </Button>
                    {agent.status !== "archived" ? (
                      <Button size="sm" variant="outline" onClick={() => archiveMutation.mutate(agent.id)}>
                        <Trash2 className="mr-2 h-4 w-4" />
                        Archive
                      </Button>
                    ) : null}
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
