"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clearAuthCookie, setAuthCookie } from "@/lib/auth";
import { normalizeApiPrefix } from "@/lib/http";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";

const loginSchema = z.object({
  apiBaseUrl: z.url(),
  apiPrefix: z.string().min(1),
  bearerToken: z.string().min(20, "Enter a valid bearer token"),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const pushToast = useToastStore((state) => state.push);
  const apiBaseUrl = useAppSettingsStore((state) => state.apiBaseUrl);
  const apiPrefix = useAppSettingsStore((state) => state.apiPrefix);
  const setSettings = useAppSettingsStore((state) => state.setSettings);
  const setAuthToken = useAppSettingsStore((state) => state.setAuthToken);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      apiBaseUrl,
      apiPrefix,
      bearerToken: "",
    },
  });

  const verifyMutation = useMutation({
    mutationFn: async (values: LoginValues) => {
      const normalizedPrefix = normalizeApiPrefix(values.apiPrefix);
      const response = await fetch(`/api/backend${normalizedPrefix}/auth/me`, {
        method: "GET",
        headers: {
          "x-airbeeps-api-base-url": values.apiBaseUrl,
          Authorization: `Bearer ${values.bearerToken}`,
        },
      });
      if (!response.ok) {
        throw new Error("Authentication failed");
      }
      return response.json() as Promise<{ workspaces: { workspace_id: string }[] }>;
    },
    onSuccess: (data, values) => {
      setSettings({
        apiBaseUrl: values.apiBaseUrl,
        apiPrefix: normalizeApiPrefix(values.apiPrefix),
      });
      setAuthToken(values.bearerToken);
      setAuthCookie(values.bearerToken);
      const firstWorkspace = data.workspaces.at(0)?.workspace_id ?? "";
      if (firstWorkspace) {
        setSettings({ workspaceId: firstWorkspace, projectId: "" });
      }
      pushToast({ title: "Signed in", description: "Session initialized successfully." });
      router.replace("/dashboard");
    },
    onError: () => {
      setAuthToken("");
      clearAuthCookie();
      pushToast({ title: "Login failed", description: "Token verification failed.", variant: "error" });
    },
  });

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Sign In</CardTitle>
        <CardDescription>Connect the dashboard with a backend bearer token.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit((values) => verifyMutation.mutate(values))(event);
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
            <Label htmlFor="bearerToken">Bearer Token</Label>
            <Input id="bearerToken" type="password" autoComplete="off" {...form.register("bearerToken")} />
          </div>
          <Button type="submit" className="w-full" disabled={verifyMutation.isPending}>
            {verifyMutation.isPending ? "Verifying..." : "Sign In"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
