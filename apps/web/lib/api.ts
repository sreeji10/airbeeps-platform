import { useAppSettingsStore } from "@/store/app-settings-store";
import { normalizeApiPrefix } from "@/lib/http";
import { z } from "zod";

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
  prompt_template_id: string | null;
  enabled_tools: string[];
  dataset_ids: string[];
  execution_limits: Record<string, unknown>;
  status: string;
  planner_model: string | null;
  generation_model: string | null;
  fallback_model: string | null;
  created_by: string;
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

export type WorkspaceMembership = {
  workspace_id: string;
  role: string;
};

export type CurrentUserResponse = {
  user_id: string;
  email: string | null;
  workspaces: WorkspaceMembership[];
};

export type WorkspaceRead = {
  id: string;
  name: string;
  created_by: string;
  created_at: string;
};

export type ProjectRead = {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  created_by: string;
  created_at: string;
};

const workspaceMembershipSchema = z.object({
  workspace_id: z.string(),
  role: z.string(),
});

const currentUserSchema = z.object({
  user_id: z.string(),
  email: z.string().nullable(),
  workspaces: z.array(workspaceMembershipSchema),
});

const workspaceReadSchema = z.object({
  id: z.string(),
  name: z.string(),
  created_by: z.string(),
  created_at: z.string(),
});

const projectReadSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  created_by: z.string(),
  created_at: z.string(),
});

const agentReadSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  project_id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  prompt_template_id: z.string().nullable(),
  enabled_tools: z.array(z.string()),
  dataset_ids: z.array(z.string()),
  execution_limits: z.record(z.string(), z.unknown()),
  status: z.string(),
  planner_model: z.string().nullable(),
  generation_model: z.string().nullable(),
  fallback_model: z.string().nullable(),
  created_by: z.string(),
  created_at: z.string(),
});

const chatSessionSchema = z.object({
  chat_id: z.string(),
  workspace_id: z.string(),
  project_id: z.string(),
  title: z.string().nullable(),
  created_at: z.string(),
});

const chatMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  created_by: z.string(),
  created_at: z.string(),
});

const chatHistorySchema = z.object({
  chat_id: z.string(),
  messages: z.array(chatMessageSchema),
});

function buildProxyPath(path: string, query?: RequestOptions["query"]): string {
  const { apiPrefix } = useAppSettingsStore.getState();
  const prefix = normalizeApiPrefix(apiPrefix);
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

async function request<T>(
  path: string,
  options: RequestOptions = {},
  schema?: z.ZodType<T>,
): Promise<T> {
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

  const json = (await response.json()) as unknown;
  if (!schema) {
    return json as T;
  }
  return schema.parse(json);
}

export const api = {
  getMe() {
    return request<CurrentUserResponse>("/auth/me", {}, currentUserSchema);
  },
  listWorkspaces() {
    return request<WorkspaceRead[]>("/workspaces", {}, z.array(workspaceReadSchema));
  },
  listProjects(workspaceId: string) {
    return request<ProjectRead[]>("/projects", {
      query: { workspace_id: workspaceId },
    }, z.array(projectReadSchema));
  },
  listAgents(workspaceId: string, projectId: string) {
    return request<AgentRead[]>("/agents", {
      query: { workspace_id: workspaceId, project_id: projectId },
    }, z.array(agentReadSchema));
  },
  createAgent(payload: {
    workspace_id: string;
    project_id: string;
    name: string;
    description?: string;
  }) {
    return request<AgentRead>(
      "/agents",
      {
        method: "POST",
        body: {
          workspace_id: payload.workspace_id,
          project_id: payload.project_id,
          name: payload.name,
          description: payload.description ?? null,
          planner_model: null,
          generation_model: null,
          fallback_model: null,
          prompt_template_id: null,
          enabled_tools: [],
          dataset_ids: [],
          execution_limits: {},
        },
      },
      agentReadSchema,
    );
  },
  createChatSession(workspaceId: string, projectId: string, title?: string) {
    return request<ChatSessionResponse>("/chat/sessions", {
      method: "POST",
      body: {
        workspace_id: workspaceId,
        project_id: projectId,
        title,
      },
    }, chatSessionSchema);
  },
  getChatHistory(chatId: string, workspaceId: string) {
    return request<ChatHistoryResponse>(`/chat/sessions/${chatId}/messages`, {
      query: { workspace_id: workspaceId },
    }, chatHistorySchema);
  },
};

export function getApiConfig() {
  const { apiBaseUrl, apiPrefix, authToken } = useAppSettingsStore.getState();
  return {
    baseUrl: apiBaseUrl,
    apiPrefix: normalizeApiPrefix(apiPrefix),
    authToken,
  };
}
