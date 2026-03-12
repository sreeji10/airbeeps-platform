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
  chats: {
    sessions: (workspaceId: string, projectId: string) => ["chat", "sessions", workspaceId, projectId] as const,
    history: (chatId: string, workspaceId: string) => ["chat", "history", chatId, workspaceId] as const,
  },
  jobs: {
    list: (workspaceId: string, projectId: string) => ["jobs", workspaceId, projectId] as const,
  },
  datasets: {
    list: (workspaceId: string, projectId: string) => ["datasets", workspaceId, projectId] as const,
  },
  usage: {
    summary: (workspaceId: string, projectId: string) => ["usage", "summary", workspaceId, projectId] as const,
  },
};
