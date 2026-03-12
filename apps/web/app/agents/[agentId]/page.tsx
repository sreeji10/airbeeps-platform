"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Save } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";

type FormValues = {
  name: string;
  description: string;
  plannerModel: string;
  generationModel: string;
  fallbackModel: string;
  status: string;
  enabledTools: string;
  datasetIds: string;
  maxToolIterations: string;
};

function splitCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function AgentDetailPage() {
  const queryClient = useQueryClient();
  const params = useParams<{ agentId: string }>();
  const agentId = params.agentId;

  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const pushToast = useToastStore((state) => state.push);

  const agentQuery = useQuery({
    queryKey: ["agent", agentId, workspaceId],
    queryFn: () => api.getAgent(agentId, workspaceId),
    enabled: Boolean(agentId) && workspaceId.trim().length > 0,
  });

  const form = useForm<FormValues>({
    defaultValues: {
      name: "",
      description: "",
      plannerModel: "",
      generationModel: "",
      fallbackModel: "",
      status: "active",
      enabledTools: "",
      datasetIds: "",
      maxToolIterations: "",
    },
  });

  useEffect(() => {
    if (!agentQuery.data) {
      return;
    }
    form.reset({
      name: agentQuery.data.name,
      description: agentQuery.data.description ?? "",
      plannerModel: agentQuery.data.planner_model ?? "",
      generationModel: agentQuery.data.generation_model ?? "",
      fallbackModel: agentQuery.data.fallback_model ?? "",
      status: agentQuery.data.status,
      enabledTools: agentQuery.data.enabled_tools.join(", "),
      datasetIds: agentQuery.data.dataset_ids.join(", "),
      maxToolIterations:
        typeof agentQuery.data.execution_limits.max_tool_iterations === "number"
          ? String(agentQuery.data.execution_limits.max_tool_iterations)
          : "",
    });
  }, [agentQuery.data, form]);

  const updateMutation = useMutation({
    mutationFn: (values: FormValues) =>
      api.updateAgent(agentId, workspaceId, {
        name: values.name,
        description: values.description || undefined,
        planner_model: values.plannerModel || undefined,
        generation_model: values.generationModel || undefined,
        fallback_model: values.fallbackModel || undefined,
        enabled_tools: splitCsv(values.enabledTools),
        dataset_ids: splitCsv(values.datasetIds),
        execution_limits: values.maxToolIterations
          ? {
              max_tool_iterations: Number(values.maxToolIterations),
            }
          : {},
        status: values.status,
      }),
    onSuccess: () => {
      pushToast({ title: "Agent updated" });
      void queryClient.invalidateQueries({ queryKey: queryKeys.agents.list(workspaceId, projectId) });
      void queryClient.invalidateQueries({ queryKey: ["agent", agentId, workspaceId] });
    },
    onError: (error) => {
      pushToast({ title: "Failed to update agent", description: String(error), variant: "error" });
    },
  });

  if (!workspaceId) {
    return <div className="text-sm text-muted-foreground">Select a workspace first.</div>;
  }

  if (agentQuery.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading agent...</div>;
  }

  if (agentQuery.isError || !agentQuery.data) {
    return <div className="text-sm text-destructive">Unable to load agent details.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/agents" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">Agent Detail</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{agentQuery.data.name}</CardTitle>
          <CardDescription>ID: {agentQuery.data.id}</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void form.handleSubmit((values) => updateMutation.mutate(values))(event);
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input {...form.register("name")} />
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select {...form.register("status")}>
                  <option value="active">active</option>
                  <option value="paused">paused</option>
                  <option value="archived">archived</option>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea className="min-h-24" {...form.register("description")} />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Planner Model</Label>
                <Input {...form.register("plannerModel")} />
              </div>
              <div className="space-y-2">
                <Label>Generation Model</Label>
                <Input {...form.register("generationModel")} />
              </div>
              <div className="space-y-2">
                <Label>Fallback Model</Label>
                <Input {...form.register("fallbackModel")} />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Enabled Tools (comma separated)</Label>
              <Input {...form.register("enabledTools")} />
            </div>

            <div className="space-y-2">
              <Label>Dataset IDs (comma separated)</Label>
              <Input {...form.register("datasetIds")} />
            </div>

            <div className="space-y-2">
              <Label>Max Tool Iterations</Label>
              <Input type="number" {...form.register("maxToolIterations")} />
            </div>

            <Button type="submit" disabled={updateMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
