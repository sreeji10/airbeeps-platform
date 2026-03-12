"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { clearAuthCookie } from "@/lib/auth";
import { useAppSettingsStore } from "@/store/app-settings-store";

type SessionBootstrapProps = {
  children: React.ReactNode;
};

export function SessionBootstrap({ children }: SessionBootstrapProps) {
  const router = useRouter();
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const clearSession = useAppSettingsStore((state) => state.clearSession);
  const setWorkspaceId = useAppSettingsStore((state) => state.setWorkspaceId);
  const setProjectId = useAppSettingsStore((state) => state.setProjectId);

  const meQuery = useQuery({
    queryKey: queryKeys.auth.me,
    queryFn: api.getMe,
    enabled: authToken.trim().length > 0,
    retry: 0,
  });

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects.list(workspaceId || "none"),
    queryFn: () => api.listProjects(workspaceId),
    enabled: authToken.trim().length > 0 && workspaceId.trim().length > 0,
  });

  useEffect(() => {
    if (meQuery.isError) {
      clearSession();
      clearAuthCookie();
      router.replace("/login");
    }
  }, [clearSession, meQuery.isError, router]);

  useEffect(() => {
    if (!meQuery.data) {
      return;
    }
    if (meQuery.data.workspaces.length === 0) {
      setWorkspaceId("");
      setProjectId("");
      return;
    }
    if (!workspaceId) {
      const fallbackWorkspace = meQuery.data.workspaces[0]?.workspace_id ?? "";
      if (fallbackWorkspace) {
        setWorkspaceId(fallbackWorkspace);
      }
      return;
    }
    if (!meQuery.data.workspaces.some((item) => item.workspace_id === workspaceId)) {
      const fallbackWorkspace = meQuery.data.workspaces[0]?.workspace_id ?? "";
      setWorkspaceId(fallbackWorkspace);
      setProjectId("");
    }
  }, [meQuery.data, setProjectId, setWorkspaceId, workspaceId]);

  useEffect(() => {
    if (!projectsQuery.data || projectsQuery.data.length === 0) {
      return;
    }
    if (!projectId) {
      setProjectId(projectsQuery.data[0].id);
      return;
    }
    if (!projectsQuery.data.some((project) => project.id === projectId)) {
      setProjectId(projectsQuery.data[0].id);
    }
  }, [projectId, projectsQuery.data, setProjectId]);

  return <>{children}</>;
}
