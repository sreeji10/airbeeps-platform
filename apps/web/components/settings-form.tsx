"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const settingsSchema = z.object({
  apiBaseUrl: z.url(),
  workspaceId: z.string().min(1),
  projectId: z.string().min(1),
});

type SettingsValues = z.infer<typeof settingsSchema>;

export function SettingsForm() {
  const form = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
      workspaceId: process.env.NEXT_PUBLIC_DEFAULT_WORKSPACE_ID ?? "workspace-demo",
      projectId: process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID ?? "project-demo",
    },
  });

  const onSubmit = (values: SettingsValues) => {
    localStorage.setItem("airbeeps_frontend_settings", JSON.stringify(values));
  };

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Platform Settings</CardTitle>
        <CardDescription>Saved locally. This is the initial configuration scaffold.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="space-y-2">
            <Label htmlFor="apiBaseUrl">API Base URL</Label>
            <Input id="apiBaseUrl" {...form.register("apiBaseUrl")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="workspaceId">Default Workspace ID</Label>
            <Input id="workspaceId" {...form.register("workspaceId")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="projectId">Default Project ID</Label>
            <Input id="projectId" {...form.register("projectId")} />
          </div>
          <Button type="submit">Save Settings</Button>
        </form>
      </CardContent>
    </Card>
  );
}
