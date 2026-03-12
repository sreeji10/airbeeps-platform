"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, Send } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import { streamChatTurn } from "@/lib/sse";
import { cn } from "@/lib/utils";

type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "streaming" | "done" | "error";
};

const DEMO_WORKSPACE_ID = process.env.NEXT_PUBLIC_DEFAULT_WORKSPACE_ID ?? "workspace-demo";
const DEMO_PROJECT_ID = process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID ?? "project-demo";

function newMessageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function ChatShell() {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [chatId, setChatId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sessionMutation = useMutation({
    mutationFn: () => api.createChatSession(DEMO_WORKSPACE_ID, DEMO_PROJECT_ID, "New Chat"),
  });

  const isStreaming = useMemo(
    () => messages.some((message) => message.role === "assistant" && message.status === "streaming"),
    [messages],
  );

  const handleSend = async () => {
    if (!input.trim() || isStreaming) {
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

    const activeChatId = chatId ?? (await sessionMutation.mutateAsync()).chat_id;
    setChatId(activeChatId);

    const abortController = new AbortController();
    abortRef.current = abortController;

    try {
      await streamChatTurn({
        chatId: activeChatId,
        workspaceId: DEMO_WORKSPACE_ID,
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
    } finally {
      abortRef.current = null;
    }
  };

  return (
    <Card className="h-[calc(100vh-9rem)]">
      <CardHeader>
        <CardTitle>Platform Chat</CardTitle>
      </CardHeader>
      <CardContent className="flex h-[calc(100%-5rem)] flex-col gap-4">
        <ScrollArea className="flex-1 rounded-lg border bg-background/80 p-4">
          <div className="space-y-3">
            {messages.length === 0 ? (
              <p className="text-sm text-muted-foreground">Start a conversation with your workspace agent runtime.</p>
            ) : null}
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                  message.role === "user"
                    ? "ml-auto bg-primary text-primary-foreground"
                    : "bg-muted text-foreground",
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
            disabled={isStreaming}
          />
          <Button onClick={() => void handleSend()} disabled={isStreaming || input.trim().length === 0}>
            {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
