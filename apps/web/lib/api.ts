const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const API_PREFIX = process.env.NEXT_PUBLIC_API_PREFIX ?? "/v1";

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

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${API_PREFIX}${path}`, API_BASE_URL);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

function getAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("airbeeps_auth_token");
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = getAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
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
  return {
    baseUrl: API_BASE_URL,
    apiPrefix: API_PREFIX,
  };
}
