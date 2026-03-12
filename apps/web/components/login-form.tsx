"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clearAuthCookie, setAuthCookie } from "@/lib/auth";
import { normalizeApiPrefix } from "@/lib/http";
import { cn } from "@/lib/utils";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";

const loginSchema = z.object({
  apiBaseUrl: z.url(),
  apiPrefix: z.string().min(1),
  email: z.string(),
  password: z.string(),
  bearerToken: z.string(),
});

type LoginValues = z.infer<typeof loginSchema>;

type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error_description?: string;
  error?: string;
};

async function readApiError(response: Response): Promise<string> {
  const fallback = `Request failed (${response.status})`;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
    if (payload?.detail) {
      return payload.detail;
    }
    if (payload?.error_description) {
      return payload.error_description;
    }
    if (payload?.message) {
      return payload.message;
    }
    if (payload?.error) {
      return payload.error;
    }
    return fallback;
  }

  const text = (await response.text().catch(() => "")).trim();
  return text || fallback;
}

export function LoginForm() {
  const router = useRouter();
  const pushToast = useToastStore((state) => state.push);
  const apiBaseUrl = useAppSettingsStore((state) => state.apiBaseUrl);
  const apiPrefix = useAppSettingsStore((state) => state.apiPrefix);
  const setSettings = useAppSettingsStore((state) => state.setSettings);
  const setAuthToken = useAppSettingsStore((state) => state.setAuthToken);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      apiBaseUrl,
      apiPrefix,
      email: "",
      password: "",
      bearerToken: "",
    },
  });

  const finalizeLogin = async (token: string, values: LoginValues) => {
    const normalizedPrefix = normalizeApiPrefix(values.apiPrefix);
    const meResponse = await fetch(`/api/backend${normalizedPrefix}/auth/me`, {
      method: "GET",
      headers: {
        "x-airbeeps-api-base-url": values.apiBaseUrl,
        Authorization: `Bearer ${token}`,
      },
    });
    if (!meResponse.ok) {
      throw new Error("Token verification failed");
    }
    const meData = (await meResponse.json()) as { workspaces: { workspace_id: string }[] };

    setSettings({
      apiBaseUrl: values.apiBaseUrl,
      apiPrefix: normalizedPrefix,
      workspaceId: meData.workspaces.at(0)?.workspace_id ?? "",
      projectId: "",
    });
    setAuthToken(token);
    setAuthCookie(token);
    pushToast({ title: "Signed in", description: "Session initialized successfully." });
    router.replace("/dashboard");
  };

  const passwordLoginMutation = useMutation({
    mutationFn: async (values: LoginValues) => {
      if (!values.email || !values.password) {
        throw new Error("Email and password are required");
      }
      const normalizedPrefix = normalizeApiPrefix(values.apiPrefix);
      const response = await fetch(`/api/backend${normalizedPrefix}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-airbeeps-api-base-url": values.apiBaseUrl,
        },
        body: JSON.stringify({
          email: values.email,
          password: values.password,
        }),
      });
      if (!response.ok) {
        const detail = await readApiError(response);
        if (response.status === 404) {
          throw new Error("Backend is missing /v1/auth/login. Restart the API server with the latest code.");
        }
        throw new Error(detail);
      }
      const payload = (await response.json()) as { access_token: string };
      if (!payload.access_token) {
        throw new Error("Auth provider returned no token");
      }
      await finalizeLogin(payload.access_token, values);
    },
    onError: (error) => {
      setAuthToken("");
      clearAuthCookie();
      pushToast({
        title: "Login failed",
        description: error instanceof Error ? error.message : String(error),
        variant: "error",
      });
    },
  });

  const tokenLoginMutation = useMutation({
    mutationFn: async (values: LoginValues) => {
      const token = values.bearerToken.trim();
      if (!token) {
        throw new Error("Enter a bearer token");
      }
      await finalizeLogin(token, values);
    },
    onError: (error) => {
      setAuthToken("");
      clearAuthCookie();
      pushToast({
        title: "Token login failed",
        description: error instanceof Error ? error.message : String(error),
        variant: "error",
      });
    },
  });

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Sign In</CardTitle>
        <CardDescription>Use your account email/password. Token login is available for debugging.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            void form.handleSubmit((values) => passwordLoginMutation.mutate(values))(event);
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
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" autoComplete="current-password" {...form.register("password")} />
          </div>
          <Button type="submit" className="w-full" disabled={passwordLoginMutation.isPending || tokenLoginMutation.isPending}>
            {passwordLoginMutation.isPending ? "Signing in..." : "Sign In"}
          </Button>

          <button
            type="button"
            className="flex w-full items-center justify-center gap-1 text-xs text-muted-foreground"
            onClick={() => setAdvancedOpen((open) => !open)}
          >
            Advanced: Use bearer token
            <ChevronDown className={cn("h-3 w-3 transition-transform", advancedOpen ? "rotate-180" : "rotate-0")} />
          </button>

          {advancedOpen ? (
            <div className="space-y-2 rounded-md border p-3">
              <Label htmlFor="bearerToken">Bearer Token</Label>
              <Input id="bearerToken" type="password" autoComplete="off" {...form.register("bearerToken")} />
              <Button
                type="button"
                variant="outline"
                className="w-full"
                disabled={passwordLoginMutation.isPending || tokenLoginMutation.isPending}
                onClick={() => {
                  void form.handleSubmit((values) => tokenLoginMutation.mutate(values))();
                }}
              >
                {tokenLoginMutation.isPending ? "Verifying token..." : "Use Token"}
              </Button>
            </div>
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}
