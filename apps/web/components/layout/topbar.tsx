"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LogOut, Menu } from "lucide-react";
import { useEffect } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";
import { clearAuthCookie } from "@/lib/auth";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";
import { useUiStore } from "@/store/ui-store";

export function Topbar() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const setWorkspaceId = useAppSettingsStore((state) => state.setWorkspaceId);
  const setProjectId = useAppSettingsStore((state) => state.setProjectId);
  const clearSession = useAppSettingsStore((state) => state.clearSession);
  const pushToast = useToastStore((state) => state.push);

  const workspacesQuery = useQuery({
    queryKey: queryKeys.workspaces.list,
    queryFn: api.listWorkspaces,
    enabled: authToken.trim().length > 0,
  });

  const workspaceOptions = workspacesQuery.data ?? [];

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects.list(workspaceId || "none"),
    queryFn: () => api.listProjects(workspaceId),
    enabled: authToken.trim().length > 0 && workspaceId.trim().length > 0,
  });

  const projectOptions = projectsQuery.data ?? [];

  useEffect(() => {
    if (!workspaceOptions.length) {
      return;
    }
    if (!workspaceId) {
      setWorkspaceId(workspaceOptions[0].id);
      return;
    }
    if (!workspaceOptions.some((item) => item.id === workspaceId)) {
      setWorkspaceId(workspaceOptions[0].id);
      setProjectId("");
    }
  }, [setProjectId, setWorkspaceId, workspaceId, workspaceOptions]);

  useEffect(() => {
    if (!projectOptions.length) {
      return;
    }
    if (!projectId) {
      setProjectId(projectOptions[0].id);
      return;
    }
    if (!projectOptions.some((item) => item.id === projectId)) {
      setProjectId(projectOptions[0].id);
    }
  }, [projectId, projectOptions, setProjectId]);

  const onLogout = () => {
    clearSession();
    clearAuthCookie();
    void queryClient.clear();
    pushToast({ title: "Signed out" });
    router.replace("/login");
  };

  return (
    <header className="flex h-16 items-center gap-3 border-b border-border/70 bg-card/60 px-4 backdrop-blur-sm">
      <Button variant="ghost" size="icon" onClick={toggleSidebar} aria-label="Toggle sidebar">
        <Menu className="h-4 w-4" />
      </Button>
      <Input placeholder="Search agents, runs, knowledge..." className="max-w-md" />
      <div className="ml-auto flex items-center gap-2">
        <Select
          className="w-48"
          value={workspaceId}
          onChange={(event) => {
            setWorkspaceId(event.target.value);
            setProjectId("");
            void queryClient.invalidateQueries({ queryKey: queryKeys.projects.list(event.target.value) });
            void queryClient.invalidateQueries({ queryKey: queryKeys.agents.list(event.target.value, "none") });
          }}
        >
          {workspaceOptions.length === 0 ? <option value="">No workspace</option> : null}
          {workspaceOptions.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </option>
          ))}
        </Select>
        <Select className="w-48" value={projectId} onChange={(event) => setProjectId(event.target.value)}>
          {projectOptions.length === 0 ? <option value="">No project</option> : null}
          {projectOptions.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </Select>
        <Link href="/settings" className={cn(buttonVariants({ variant: "outline" }))}>
          Settings
        </Link>
        <Button variant="outline" size="icon" onClick={onLogout} aria-label="Sign out">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
