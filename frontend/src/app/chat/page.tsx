"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { FileText } from "lucide-react";

import { api } from "@/lib/api";
import { UploadZone } from "@/components/upload-zone";
import { ChatThread, type ChatMessage } from "@/components/chat-thread";

export default function ChatPage() {
  const { getToken } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);

  async function token(): Promise<string> {
    const t = await getToken();
    if (!t) throw new Error("Not authenticated");
    return t;
  }

  async function handleUpload(file: File) {
    const res = await api.upload(await token(), file, sessionId ?? undefined);
    setSessionId(res.session_id);
    setFileName(res.file.filename);
    setMessages([
      {
        id: `sys-${res.file.id}`,
        role: "system",
        content: `“${res.file.filename}” is ready — ${res.chunks_stored} chunks indexed. Ask anything about it.`,
      },
    ]);
  }

  async function handleSend(text: string) {
    if (!sessionId) return;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setPending(true);
    try {
      const res = await api.chat(await token(), sessionId, text);
      setMessages((m) => [
        ...m,
        { id: res.message_id, role: "assistant", content: res.answer, sources: res.sources },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content:
            e instanceof Error ? `⚠️ ${e.message}` : "⚠️ Something went wrong. Please try again.",
        },
      ]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
        <h1 className="text-lg font-semibold">Workspace</h1>
        {fileName && (
          <span className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
            <FileText className="h-3.5 w-3.5 text-[var(--color-brand)]" />
            {fileName}
          </span>
        )}
      </header>

      {sessionId ? (
        <ChatThread messages={messages} pending={pending} onSend={handleSend} />
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <h2 className="mb-2 text-xl font-semibold">
            Upload a document to begin chatting
          </h2>
          <p className="mb-6 max-w-md text-sm text-[var(--color-muted)]">
            Drop a PDF and ask questions in plain language. SmartDocZ retrieves
            the right passages and answers with page citations.
          </p>
          <UploadZone onUpload={handleUpload} />
        </div>
      )}
    </div>
  );
}
