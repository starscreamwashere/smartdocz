"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, FileText } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Source } from "@/lib/api";
import { Button } from "@/components/ui/button";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: Source[];
}

export function ChatThread({
  messages,
  pending,
  onSend,
}: {
  messages: ChatMessage[];
  pending: boolean;
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  function submit() {
    const value = text.trim();
    if (!value || pending) return;
    onSend(value);
    setText("");
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-5">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {pending && (
            <div className="flex items-center gap-2 text-sm text-[var(--color-muted)]">
              <Loader2 className="h-4 w-4 animate-spin" /> Thinking…
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-[var(--color-border)] px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Ask a question about your document…"
            className="max-h-40 min-h-[44px] flex-1 resize-none rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm outline-none placeholder:text-[var(--color-muted)] focus:border-[var(--color-brand)]"
          />
          <Button onClick={submit} disabled={pending || !text.trim()} className="h-11">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex flex-col", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[85%] whitespace-pre-wrap rounded-[var(--radius)] px-4 py-2.5 text-sm",
          isUser
            ? "bg-[var(--color-brand)] text-[var(--color-brand-foreground)]"
            : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-foreground)]",
        )}
      >
        {message.content}
      </div>

      {message.sources && message.sources.length > 0 && (
        <div className="mt-2 flex max-w-[85%] flex-wrap gap-1.5">
          {dedupePages(message.sources).map((page) => (
            <span
              key={page}
              className="flex items-center gap-1 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 font-mono text-[11px] text-[var(--color-muted)]"
            >
              <FileText className="h-3 w-3" /> Page {page}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function dedupePages(sources: Source[]): number[] {
  return [...new Set(sources.map((s) => s.page_number))].filter((p) => p > 0).sort((a, b) => a - b);
}
