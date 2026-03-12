import { useAppSettingsStore } from "@/store/app-settings-store";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  query?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
  headers?: HeadersInit;
};

export type AgentRead = {
  id: string;
  workspace_id: string;
  project_id: string;
  name: string;
  description: string | null;
  status: string;
  planner_model: string | null;
  generation_model: string | null;
  fallback_model: string | null;
  created_at: string;
};

export type ChatSessionResponse = {
  chat_id: string;
  workspace_id: string;
  project_id: string;
  title: string | null;
  created_at: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_by: string;
  created_at: string;
};

export type ChatHistoryResponse = {
  chat_id: string;
  messages: ChatMessage[];
};

function normalizePrefix(prefix: string): string {
  const trimmed = prefix.trim();
  if (!trimmed) {
    return "/v1";
  }
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}

function buildProxyPath(path: string, query?: RequestOptions["query"]): string {
  const { apiPrefix } = useAppSettingsStore.getState();
  const prefix = normalizePrefix(apiPrefix);
  const finalPath = path.startsWith("/") ? path : `/${path}`;
  const search = new URLSearchParams();
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined) {
        search.set(key, String(value));
      }
    });
  }
  const queryString = search.toString();
  return `/api/backend${prefix}${finalPath}${queryString ? `?${queryString}` : ""}`;
}

function getProxyHeaders(input?: HeadersInit): Headers {
  const { apiBaseUrl, authToken } = useAppSettingsStore.getState();
  const headers = new Headers(input);
  headers.set("Content-Type", "application/json");
  headers.set("x-airbeeps-api-base-url", apiBaseUrl);
  if (authToken.trim()) {
    headers.set("Authorization", `Bearer ${authToken.trim()}`);
  }
  return headers;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(buildProxyPath(path, options.query), {
    method: options.method ?? "GET",
    headers: getProxyHeaders(options.headers),
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail || "Request failed"}`);
  }

  return (await response.json()) as T;
}

export const api = {
  listAgents(workspaceId: string, projectId: string) {
    return request<AgentRead[]>("/agents", {
      query: { workspace_id: workspaceId, project_id: projectId },
    });
  },
  createChatSession(workspaceId: string, projectId: string, title?: string) {
    return request<ChatSessionResponse>("/chat/sessions", {
      method: "POST",
      body: {
        workspace_id: workspaceId,
        project_id: projectId,
        title,
      },
    });
  },
  getChatHistory(chatId: string, workspaceId: string) {
    return request<ChatHistoryResponse>(`/chat/sessions/${chatId}/messages`, {
      query: { workspace_id: workspaceId },
    });
  },
};

export function getApiConfig() {
  const { apiBaseUrl, apiPrefix, authToken } = useAppSettingsStore.getState();
  return {
    baseUrl: apiBaseUrl,
    apiPrefix: normalizePrefix(apiPrefix),
    authToken,
  };
}
