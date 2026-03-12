export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  workspaces: {
    list: ["workspaces"] as const,
  },
  projects: {
    list: (workspaceId: string) => ["projects", workspaceId] as const,
  },
  agents: {
    list: (workspaceId: string, projectId: string) => ["agents", workspaceId, projectId] as const,
  },
};
