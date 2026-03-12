"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAppSettingsStore } from "@/store/app-settings-store";

const settingsSchema = z.object({
  apiBaseUrl: z.url(),
  apiPrefix: z.string().min(1),
  workspaceId: z.string().min(1),
  projectId: z.string().min(1),
  authToken: z.string(),
});

type SettingsValues = z.infer<typeof settingsSchema>;

export function SettingsForm() {
  const apiBaseUrl = useAppSettingsStore((state) => state.apiBaseUrl);
  const apiPrefix = useAppSettingsStore((state) => state.apiPrefix);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const authToken = useAppSettingsStore((state) => state.authToken);
  const setSettings = useAppSettingsStore((state) => state.setSettings);
  const resetSettings = useAppSettingsStore((state) => state.resetSettings);
  const settings = useMemo(
    () => ({ apiBaseUrl, apiPrefix, workspaceId, projectId, authToken }),
    [apiBaseUrl, apiPrefix, workspaceId, projectId, authToken],
  );

  const form = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: settings,
  });

  useEffect(() => {
    form.reset(settings);
  }, [form, settings]);

  const onSubmit = (values: SettingsValues) => {
    setSettings(values);
  };

  const onReset = () => {
    resetSettings();
  };

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Platform Settings</CardTitle>
        <CardDescription>
          Persistent frontend context used by all API and SSE calls through the Next.js proxy.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit(onSubmit)(event);
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="apiBaseUrl">API Base URL</Label>
            <Input id="apiBaseUrl" {...form.register("apiBaseUrl")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="apiPrefix">API Prefix</Label>
            <Input id="apiPrefix" {...form.register("apiPrefix")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="workspaceId">Default Workspace ID</Label>
            <Input id="workspaceId" {...form.register("workspaceId")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="projectId">Default Project ID</Label>
            <Input id="projectId" {...form.register("projectId")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="authToken">Bearer Token</Label>
            <Input id="authToken" type="password" autoComplete="off" {...form.register("authToken")} />
          </div>
          <div className="flex gap-2">
            <Button type="submit">Save Settings</Button>
            <Button type="button" variant="secondary" onClick={onReset}>
              Reset Defaults
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
