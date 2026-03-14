"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Send, Square } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { streamChatTurn } from "@/lib/sse";
import { useAppSettingsStore } from "@/store/app-settings-store";
import { useToastStore } from "@/store/toast-store";
import { cn } from "@/lib/utils";

type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "streaming" | "done" | "error";
};

type RunMeta = {
  runId: string;
  planId: string;
  status: string;
  events: string[];
};

function newMessageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function ChatShell() {
  const queryClient = useQueryClient();
  const authToken = useAppSettingsStore((state) => state.authToken);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);
  const pushToast = useToastStore((state) => state.push);

  const [input, setInput] = useState("");
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [streamState, setStreamState] = useState<"idle" | "streaming" | "error">("idle");
  const [runMeta, setRunMeta] = useState<RunMeta | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sessionsQuery = useQuery({
    queryKey: queryKeys.chats.sessions(workspaceId || "none", projectId || "none"),
    queryFn: () => api.listChatSessions(workspaceId, projectId),
    enabled: authToken.trim().length > 0 && workspaceId.trim().length > 0 && projectId.trim().length > 0,
  });

  const historyQuery = useQuery({
    queryKey: queryKeys.chats.history(selectedChatId || "none", workspaceId || "none"),
    queryFn: () => api.getChatHistory(selectedChatId as string, workspaceId),
    enabled: Boolean(selectedChatId) && workspaceId.trim().length > 0,
  });

  const createSessionMutation = useMutation({
    mutationFn: () => api.createChatSession(workspaceId, projectId, "New Chat"),
    onSuccess: (session) => {
      setSelectedChatId(session.chat_id);
      void queryClient.invalidateQueries({ queryKey: queryKeys.chats.sessions(workspaceId, projectId) });
    },
  });

  useEffect(() => {
    if (!sessionsQuery.data?.sessions?.length) {
      setSelectedChatId(null);
      return;
    }
    if (!selectedChatId) {
      setSelectedChatId(sessionsQuery.data.sessions[0].chat_id);
      return;
    }
    if (!sessionsQuery.data.sessions.some((item) => item.chat_id === selectedChatId)) {
      setSelectedChatId(sessionsQuery.data.sessions[0].chat_id);
    }
  }, [selectedChatId, sessionsQuery.data]);

  useEffect(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreamState("idle");
    setInput("");
    setMessages([]);
    setSelectedChatId(null);
    setRunMeta(null);
  }, [workspaceId, projectId]);

  useEffect(() => {
    if (!historyQuery.data) {
      return;
    }
    const isUiRole = (role: "user" | "assistant" | "system"): role is "user" | "assistant" =>
      role === "user" || role === "assistant";
    setMessages(
      historyQuery.data.messages
        .filter((msg) => isUiRole(msg.role))
        .map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
          status: "done",
        })),
    );
  }, [historyQuery.data]);

  const canChat = authToken.trim().length > 0 && workspaceId.trim().length > 0 && projectId.trim().length > 0;
  const isStreaming = streamState === "streaming";

  const sessionRows = useMemo(() => sessionsQuery.data?.sessions ?? [], [sessionsQuery.data]);

  const createSessionIfMissing = async (): Promise<string> => {
    if (selectedChatId) {
      return selectedChatId;
    }
    const session = await createSessionMutation.mutateAsync();
    return session.chat_id;
  };

  const stopStreaming = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreamState("idle");
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming || !canChat) {
      return;
    }

    const prompt = input.trim();
    setInput("");

    const userMessage: UiMessage = {
      id: newMessageId(),
      role: "user",
      content: prompt,
      status: "done",
    };
    const assistantMessage: UiMessage = {
      id: newMessageId(),
      role: "assistant",
      content: "",
      status: "streaming",
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setStreamState("streaming");
    setRunMeta({
      runId: "-",
      planId: "-",
      status: "streaming",
      events: [`${new Date().toLocaleTimeString()}: request started`],
    });

    const chatId = await createSessionIfMissing();
    setSelectedChatId(chatId);

    const abortController = new AbortController();
    abortRef.current = abortController;
    let hasError = false;

    try {
      await streamChatTurn({
        chatId,
        workspaceId,
        content: prompt,
        signal: abortController.signal,
        onEvent: (event, payload) => {
          if (event === "token") {
            const tokenPayload = payload as { token?: string; content?: string };
            const token = tokenPayload.token ?? tokenPayload.content ?? "";
            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantMessage.id
                  ? {
                      ...message,
                      content: `${message.content}${token}`,
                    }
                  : message,
              ),
            );
            return;
          }

          if (event === "done") {
            const donePayload = payload as { run_id?: string; plan_id?: string; status?: string };
            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantMessage.id
                  ? {
                      ...message,
                      status: "done",
                    }
                  : message,
              ),
            );
            setStreamState("idle");
            setRunMeta((prev) => ({
              runId: donePayload.run_id ?? prev?.runId ?? "-",
              planId: donePayload.plan_id ?? prev?.planId ?? "-",
              status: donePayload.status ?? "completed",
              events: [...(prev?.events ?? []), `${new Date().toLocaleTimeString()}: completed`],
            }));
            void queryClient.invalidateQueries({ queryKey: queryKeys.chats.history(chatId, workspaceId) });
            void queryClient.invalidateQueries({ queryKey: queryKeys.chats.sessions(workspaceId, projectId) });
            return;
          }

          if (event === "status") {
            const statusPayload = payload as { status?: string; message?: string; run_id?: string; plan_id?: string };
            const statusText = statusPayload.message ?? statusPayload.status ?? "status update";
            setRunMeta((prev) => ({
              runId: statusPayload.run_id ?? prev?.runId ?? "-",
              planId: statusPayload.plan_id ?? prev?.planId ?? "-",
              status: statusPayload.status ?? prev?.status ?? "streaming",
              events: [...(prev?.events ?? []), `${new Date().toLocaleTimeString()}: ${statusText}`].slice(-8),
            }));
            return;
          }

          if (event === "error") {
            const errorPayload = payload as { detail?: string; message?: string };
            const detail = errorPayload.detail ?? errorPayload.message ?? "Stream failed";
            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantMessage.id
                  ? {
                      ...message,
                      content: message.content || detail,
                      status: "error",
                    }
                  : message,
              ),
            );
            setStreamState("error");
            setRunMeta((prev) => ({
              runId: prev?.runId ?? "-",
              planId: prev?.planId ?? "-",
              status: "error",
              events: [...(prev?.events ?? []), `${new Date().toLocaleTimeString()}: ${detail}`].slice(-8),
            }));
            hasError = true;
          }
        },
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Stream failed";
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantMessage.id
            ? {
                ...message,
                content: message.content || detail,
                status: "error",
              }
            : message,
        ),
      );
      setStreamState("error");
      setRunMeta((prev) => ({
        runId: prev?.runId ?? "-",
        planId: prev?.planId ?? "-",
        status: "error",
        events: [...(prev?.events ?? []), `${new Date().toLocaleTimeString()}: ${detail}`].slice(-8),
      }));
      hasError = true;
      pushToast({ title: "Chat stream failed", description: detail, variant: "error" });
    } finally {
      abortRef.current = null;
      if (!hasError) {
        setStreamState("idle");
      }
    }
  };

  return (
    <Card className="h-[calc(100vh-9rem)]">
      <CardHeader className="border-b pb-4">
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Platform Chat</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => void createSessionMutation.mutateAsync()}
              disabled={!canChat || createSessionMutation.isPending || isStreaming}
            >
              <Plus className="mr-2 h-4 w-4" />
              New Session
            </Button>
            {isStreaming ? (
              <Button variant="outline" onClick={stopStreaming}>
                <Square className="mr-2 h-4 w-4" />
                Stop
              </Button>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid h-[calc(100%-5rem)] grid-cols-1 gap-4 pt-4 md:grid-cols-[240px_1fr]">
        <div className="rounded-lg border bg-background/70 p-2">
          <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Sessions</div>
          <ScrollArea className="h-[calc(100%-1.5rem)]">
            <div className="space-y-1">
              {sessionRows.map((session) => (
                <button
                  key={session.chat_id}
                  type="button"
                  onClick={() => {
                    if (!isStreaming) {
                      setSelectedChatId(session.chat_id);
                    }
                  }}
                  className={cn(
                    "w-full rounded-md px-2 py-2 text-left text-sm",
                    selectedChatId === session.chat_id ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                  )}
                  disabled={isStreaming}
                >
                  <p className="truncate">{session.title || "Untitled session"}</p>
                  <p className="truncate text-xs opacity-80">{new Date(session.created_at).toLocaleString()}</p>
                </button>
              ))}
              {sessionsQuery.isLoading ? <p className="px-2 text-xs text-muted-foreground">Loading sessions...</p> : null}
              {sessionsQuery.isError ? <p className="px-2 text-xs text-destructive">Failed to load sessions.</p> : null}
              {!sessionsQuery.isLoading && sessionRows.length === 0 ? (
                <p className="px-2 text-xs text-muted-foreground">No chat sessions yet.</p>
              ) : null}
            </div>
          </ScrollArea>
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-lg border bg-card p-3 text-xs">
            <p className="font-semibold">Run Metadata</p>
            <p className="text-muted-foreground">Run ID: {runMeta?.runId ?? "-"}</p>
            <p className="text-muted-foreground">Plan ID: {runMeta?.planId ?? "-"}</p>
            <p className="text-muted-foreground">Status: {runMeta?.status ?? "idle"}</p>
            {runMeta?.events?.length ? (
              <div className="mt-2 space-y-1">
                {runMeta.events.map((event, idx) => (
                  <p key={`${event}-${idx}`} className="text-muted-foreground">
                    {event}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
          <ScrollArea className="flex-1 rounded-lg border bg-background/80 p-4">
            <div className="space-y-3">
              {!canChat ? <p className="text-sm text-muted-foreground">Sign in and select a workspace/project.</p> : null}
              {canChat && historyQuery.isLoading ? <p className="text-sm text-muted-foreground">Loading messages...</p> : null}
              {canChat && historyQuery.isError ? <p className="text-sm text-destructive">Failed to load selected chat history.</p> : null}
              {messages.length === 0 && canChat && !historyQuery.isLoading ? (
                <p className="text-sm text-muted-foreground">Start a conversation with your workspace agent runtime.</p>
              ) : null}
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                    message.role === "user" ? "ml-auto bg-primary text-primary-foreground" : "bg-muted text-foreground",
                  )}
                >
                  <p className="whitespace-pre-wrap">{message.content || (message.status === "streaming" ? "..." : "")}</p>
                </div>
              ))}
            </div>
          </ScrollArea>
          <div className="flex gap-2">
            <Input
              placeholder="Ask something about your project..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void handleSend();
                }
              }}
              disabled={!canChat || isStreaming}
            />
            <Button onClick={() => void handleSend()} disabled={!canChat || isStreaming || input.trim().length === 0}>
              {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
