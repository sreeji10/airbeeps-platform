"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";

const createAgentSchema = z.object({
  name: z.string().min(2).max(128),
  description: z.string().max(2000).optional(),
});

type CreateAgentValues = z.infer<typeof createAgentSchema>;

export function CreateAgentForm() {
  const queryClient = useQueryClient();
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const pushToast = useToastStore((state) => state.push);

  const form = useForm<CreateAgentValues>({
    resolver: zodResolver(createAgentSchema),
    defaultValues: {
      name: "",
      description: "",
    },
  });

  const createMutation = useMutation({
    mutationFn: (values: CreateAgentValues) =>
      api.createAgent({
        workspace_id: workspaceId,
        project_id: projectId,
        name: values.name,
        description: values.description,
      }),
    onSuccess: () => {
      pushToast({ title: "Agent created" });
      form.reset();
      void queryClient.invalidateQueries({ queryKey: queryKeys.agents.list(workspaceId, projectId) });
    },
    onError: (error) => {
      pushToast({ title: "Failed to create agent", description: String(error), variant: "error" });
    },
  });

  if (!workspaceId || !projectId) {
    return null;
  }

  return (
    <form
      className="grid gap-3 rounded-xl border bg-card p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit((values) => createMutation.mutate(values))(event);
      }}
    >
      <h3 className="text-sm font-semibold">Create Agent</h3>
      <div className="grid gap-2 md:grid-cols-[160px_1fr] md:items-center">
        <Label htmlFor="name">Name</Label>
        <Input id="name" {...form.register("name")} />
      </div>
      <div className="grid gap-2 md:grid-cols-[160px_1fr] md:items-start">
        <Label htmlFor="description">Description</Label>
        <Textarea id="description" className="min-h-20" {...form.register("description")} />
      </div>
      <div>
        <Button type="submit" disabled={createMutation.isPending}>
          {createMutation.isPending ? "Creating..." : "Create"}
        </Button>
      </div>
    </form>
  );
}
