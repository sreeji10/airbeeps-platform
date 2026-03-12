"use client";

import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useToastStore } from "@/store/toast-store";

export function Toaster() {
  const messages = useToastStore((state) => state.messages);
  const dismiss = useToastStore((state) => state.dismiss);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "pointer-events-auto rounded-lg border bg-card p-4 shadow-lg",
            message.variant === "error" && "border-destructive/60",
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold">{message.title}</p>
              {message.description ? <p className="text-xs text-muted-foreground">{message.description}</p> : null}
            </div>
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => dismiss(message.id)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
