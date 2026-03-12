import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="text-sm text-muted-foreground">
          Streaming chat UI using backend SSE events (`token`, `status`, `done`, `error`).
        </p>
      </section>
      <ChatShell />
    </div>
  );
}
