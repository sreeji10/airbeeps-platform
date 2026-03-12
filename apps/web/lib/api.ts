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

export type ChatSessionListResponse = {
  sessions: ChatSessionResponse[];
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

export type DatasetRead = {
  id: string;
  workspace_id: string;
  project_id: string;
  name: string;
  status: string;
  created_by: string;
  created_at: string;
};

export type JobRead = {
  id: string;
  workspace_id: string;
  project_id: string | null;
  kind: string;
  status: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  error: string | null;
  attempt: number;
  max_attempts: number;
  run_after: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type UsageSummaryRead = {
  workspace_id: string;
  project_id: string | null;
  request_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
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

const chatSessionListSchema = z.object({
  sessions: z.array(chatSessionSchema),
});

const datasetReadSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  project_id: z.string(),
  name: z.string(),
  status: z.string(),
  created_by: z.string(),
  created_at: z.string(),
});

const jobReadSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  project_id: z.string().nullable(),
  kind: z.string(),
  status: z.string(),
  payload: z.record(z.string(), z.unknown()),
  result: z.record(z.string(), z.unknown()),
  error: z.string().nullable(),
  attempt: z.number(),
  max_attempts: z.number(),
  run_after: z.string(),
  created_by: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

const usageSummarySchema = z.object({
  workspace_id: z.string(),
  project_id: z.string().nullable(),
  request_count: z.number(),
  prompt_tokens: z.number(),
  completion_tokens: z.number(),
  total_tokens: z.number(),
  estimated_cost_usd: z.number(),
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
  listAgents(workspaceId: string, projectId: string, includeArchived = false) {
    return request<AgentRead[]>("/agents", {
      query: { workspace_id: workspaceId, project_id: projectId, include_archived: includeArchived },
    }, z.array(agentReadSchema));
  },
  getAgent(agentId: string, workspaceId: string) {
    return request<AgentRead>(
      `/agents/${agentId}`,
      {
        query: { workspace_id: workspaceId },
      },
      agentReadSchema,
    );
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
  updateAgent(
    agentId: string,
    workspaceId: string,
    payload: {
      name: string;
      description?: string;
      planner_model?: string | null;
      generation_model?: string | null;
      fallback_model?: string | null;
      prompt_template_id?: string | null;
      enabled_tools?: string[];
      dataset_ids?: string[];
      execution_limits?: Record<string, unknown>;
      status?: string;
    },
  ) {
    return request<AgentRead>(
      `/agents/${agentId}`,
      {
        method: "PATCH",
        query: { workspace_id: workspaceId },
        body: {
          name: payload.name,
          description: payload.description ?? null,
          planner_model: payload.planner_model ?? null,
          generation_model: payload.generation_model ?? null,
          fallback_model: payload.fallback_model ?? null,
          prompt_template_id: payload.prompt_template_id ?? null,
          enabled_tools: payload.enabled_tools ?? [],
          dataset_ids: payload.dataset_ids ?? [],
          execution_limits: payload.execution_limits ?? {},
          status: payload.status ?? "active",
        },
      },
      agentReadSchema,
    );
  },
  archiveAgent(agentId: string, workspaceId: string) {
    return request<AgentRead>(
      `/agents/${agentId}`,
      {
        method: "DELETE",
        query: { workspace_id: workspaceId },
      },
      agentReadSchema,
    );
  },
  listChatSessions(workspaceId: string, projectId: string) {
    return request<ChatSessionListResponse>(
      "/chat/sessions",
      {
        query: { workspace_id: workspaceId, project_id: projectId },
      },
      chatSessionListSchema,
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
  listDatasets(workspaceId: string, projectId?: string) {
    return request<DatasetRead[]>(
      "/datasets",
      {
        query: { workspace_id: workspaceId, project_id: projectId },
      },
      z.array(datasetReadSchema),
    );
  },
  listDatasetsPage(params: {
    workspaceId: string;
    projectId?: string;
    status?: string;
    limit: number;
    offset: number;
    sort?: "asc" | "desc";
  }) {
    return request<DatasetRead[]>(
      "/datasets",
      {
        query: {
          workspace_id: params.workspaceId,
          project_id: params.projectId,
          status: params.status,
          limit: params.limit,
          offset: params.offset,
          sort: params.sort ?? "desc",
        },
      },
      z.array(datasetReadSchema),
    );
  },
  enqueueDatasetIngestion(workspaceId: string, projectId: string, datasetId: string) {
    return request<JobRead>(
      "/datasets/ingest/jobs",
      {
        method: "POST",
        body: {
          workspace_id: workspaceId,
          project_id: projectId,
          dataset_id: datasetId,
        },
      },
      jobReadSchema,
    );
  },
  listJobs(workspaceId: string, projectId?: string) {
    return request<JobRead[]>(
      "/jobs",
      {
        query: { workspace_id: workspaceId, project_id: projectId },
      },
      z.array(jobReadSchema),
    );
  },
  listJobsPage(params: {
    workspaceId: string;
    projectId?: string;
    status?: string;
    kind?: string;
    limit: number;
    offset: number;
    sort?: "asc" | "desc";
  }) {
    return request<JobRead[]>(
      "/jobs",
      {
        query: {
          workspace_id: params.workspaceId,
          project_id: params.projectId,
          status: params.status,
          kind: params.kind,
          limit: params.limit,
          offset: params.offset,
          sort: params.sort ?? "desc",
        },
      },
      z.array(jobReadSchema),
    );
  },
  getUsageSummary(workspaceId: string, projectId?: string) {
    return request<UsageSummaryRead>(
      "/usage/summary",
      {
        query: { workspace_id: workspaceId, project_id: projectId },
      },
      usageSummarySchema,
    );
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
