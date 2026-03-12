"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AppSettingsState = {
  apiBaseUrl: string;
  apiPrefix: string;
  workspaceId: string;
  projectId: string;
  authToken: string;
  setSettings: (patch: Partial<Omit<AppSettingsState, "setSettings" | "resetSettings">>) => void;
  resetSettings: () => void;
};

const DEFAULT_SETTINGS = {
  apiBaseUrl:
    process.env.NEXT_PUBLIC_API_BASE_URL && process.env.NEXT_PUBLIC_API_BASE_URL.trim()
      ? process.env.NEXT_PUBLIC_API_BASE_URL
      : "http://127.0.0.1:8000",
  apiPrefix:
    process.env.NEXT_PUBLIC_API_PREFIX && process.env.NEXT_PUBLIC_API_PREFIX.trim()
      ? process.env.NEXT_PUBLIC_API_PREFIX
      : "/v1",
  workspaceId:
    process.env.NEXT_PUBLIC_DEFAULT_WORKSPACE_ID && process.env.NEXT_PUBLIC_DEFAULT_WORKSPACE_ID.trim()
      ? process.env.NEXT_PUBLIC_DEFAULT_WORKSPACE_ID
      : "workspace-demo",
  projectId:
    process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID && process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID.trim()
      ? process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID
      : "project-demo",
  authToken: "",
};

export const useAppSettingsStore = create<AppSettingsState>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,
      setSettings: (patch) => set((state) => ({ ...state, ...patch })),
      resetSettings: () => set(DEFAULT_SETTINGS),
    }),
    {
      name: "airbeeps-app-settings",
      partialize: (state) => ({
        apiBaseUrl: state.apiBaseUrl,
        apiPrefix: state.apiPrefix,
        workspaceId: state.workspaceId,
        projectId: state.projectId,
        authToken: state.authToken,
      }),
    },
  ),
);
