import { getApiConfig } from "@/lib/api";

export type SseEventMap = {
  token: { token?: string; content?: string };
  status: { status?: string; message?: string };
  done: { chat_id?: string; run_id?: string; plan_id?: string; assistant_message_id?: string; status?: string };
  error: { message?: string; detail?: string };
};

type StreamOptions = {
  chatId: string;
  workspaceId: string;
  content: string;
  agentId?: string;
  datasetIds?: string[];
  signal?: AbortSignal;
  onEvent: <T extends keyof SseEventMap>(event: T, payload: SseEventMap[T]) => void;
};

export async function streamChatTurn(options: StreamOptions): Promise<void> {
  const { baseUrl, apiPrefix, authToken } = getApiConfig();
  const url = new URL(`/api/backend${apiPrefix}/chat/sessions/${options.chatId}/messages/stream`, window.location.origin);
  url.searchParams.set("workspace_id", options.workspaceId);

  const response = await fetch(url.toString(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-airbeeps-api-base-url": baseUrl,
      ...(authToken.trim() ? { Authorization: `Bearer ${authToken.trim()}` } : {}),
    },
    body: JSON.stringify({
      content: options.content,
      agent_id: options.agentId,
      dataset_ids: options.datasetIds ?? [],
    }),
    signal: options.signal,
  });

  if (!response.ok || !response.body) {
    const detail = await response.text();
    throw new Error(detail || "Streaming failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event:"));
      const dataLine = lines.find((line) => line.startsWith("data:"));
      if (!eventLine || !dataLine) {
        continue;
      }

      const event = eventLine.replace("event:", "").trim() as keyof SseEventMap;
      const json = dataLine.replace("data:", "").trim();

      try {
        const payload = JSON.parse(json) as SseEventMap[keyof SseEventMap];
        options.onEvent(event, payload as never);
      } catch {
        options.onEvent("error", { detail: "Invalid event payload" });
      }
    }
  }
}
