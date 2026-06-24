"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, Plus, X } from "lucide-react";

import { api, type UploadResult } from "@/lib/api";
import { UploadZone } from "@/components/upload-zone";
import { ChatThread, type ChatMessage } from "@/components/chat-thread";
import { Button } from "@/components/ui/button";

/**
 * The authenticated chat workspace.
 *
 * The active session id lives in the URL (`/chat?s=<id>`), so a refresh or a
 * shared link restores the same conversation. A ref tracks which session we
 * already hold locally so a just-created session isn't immediately re-fetched.
 * Sources (files or YouTube transcripts) can be added to a session at any time.
 */
export function ChatWorkspace() {
  const { getToken } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const sessionId = params.get("s");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [fileName, setFileName] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showUploader, setShowUploader] = useState(false);
  const loadedSession = useRef<string | null>(null);

  const token = useCallback(async () => {
    const t = await getToken();
    if (!t) throw new Error("Not authenticated");
    return t;
  }, [getToken]);

  // Restore messages when the active session changes (sidebar switch / refresh).
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      setFileName(null);
      setShowUploader(false);
      loadedSession.current = null;
      return;
    }
    if (loadedSession.current === sessionId) return;

    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const t = await token();
        const [msgs, session] = await Promise.all([
          api.messages(t, sessionId),
          api.getSession(t, sessionId),
        ]);
        if (cancelled) return;
        loadedSession.current = sessionId;
        setFileName(session.title ?? null);
        setMessages(msgs.map((m) => ({ id: m.id, role: m.role, content: m.content })));
      } catch (e) {
        if (!cancelled)
          setMessages([
            {
              id: "load-err",
              role: "assistant",
              content:
                e instanceof Error ? `⚠️ ${e.message}` : "⚠️ Failed to load this conversation.",
            },
          ]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  function applyResult(res: UploadResult) {
    setFileName(res.file.filename);
    loadedSession.current = res.session_id; // don't let the restore effect refetch
    qc.invalidateQueries({ queryKey: ["sessions"] });
    if (sessionId !== res.session_id) router.replace(`/chat?s=${res.session_id}`);
    setMessages((m) => [
      ...m,
      {
        id: `sys-${res.file.id}`,
        role: "system",
        content: `“${res.file.filename}” is ready — ${res.chunks_stored} chunks indexed. Ask anything about it.`,
      },
    ]);
    setShowUploader(false);
  }

  async function handleUploadFile(file: File) {
    applyResult(await api.upload(await token(), file, sessionId ?? undefined));
  }
  async function handleUploadYoutube(url: string) {
    applyResult(await api.uploadYoutube(await token(), url, sessionId ?? undefined));
  }

  async function handleSend(text: string) {
    if (!sessionId) return;
    setMessages((m) => [...m, { id: `u-${Date.now()}`, role: "user", content: text }]);
    setPending(true);
    try {
      const res = await api.chat(await token(), sessionId, text);
      setMessages((m) => [
        ...m,
        {
          id: res.message_id,
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          provider: res.model_provider,
          model: res.model,
        },
      ]);
      qc.invalidateQueries({ queryKey: ["sessions"] });
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: e instanceof Error ? `⚠️ ${e.message}` : "⚠️ Something went wrong.",
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
        <div className="flex items-center gap-3">
          {fileName && (
            <span className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
              <FileText className="h-3.5 w-3.5 text-[var(--color-brand)]" />
              {fileName}
            </span>
          )}
          {sessionId && !showUploader && (
            <Button variant="secondary" size="sm" onClick={() => setShowUploader(true)}>
              <Plus className="h-4 w-4" /> Add source
            </Button>
          )}
        </div>
      </header>

      {loading ? (
        <div className="flex flex-1 items-center justify-center text-sm text-[var(--color-muted)]">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading conversation…
        </div>
      ) : !sessionId ? (
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <h2 className="mb-2 text-xl font-semibold">Upload a document to begin chatting</h2>
          <p className="mb-6 max-w-md text-sm text-[var(--color-muted)]">
            Add a PDF, DOCX, TXT, CSV, JSON file or a YouTube URL. SmartDocZ
            retrieves the right passages and answers with citations.
          </p>
          <UploadZone onUploadFile={handleUploadFile} onUploadYoutube={handleUploadYoutube} />
        </div>
      ) : showUploader ? (
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <div className="mb-4 flex items-center gap-3">
            <h2 className="text-lg font-semibold">Add another source</h2>
            <Button variant="ghost" size="sm" onClick={() => setShowUploader(false)}>
              <X className="h-4 w-4" /> Cancel
            </Button>
          </div>
          <UploadZone onUploadFile={handleUploadFile} onUploadYoutube={handleUploadYoutube} />
        </div>
      ) : (
        <ChatThread messages={messages} pending={pending} onSend={handleSend} />
      )}
    </div>
  );
}
