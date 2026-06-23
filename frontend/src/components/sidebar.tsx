"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { SignOutButton, useAuth, useUser } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, BarChart3, LogOut, Trash2, MessageSquare, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { api, type ApiSessionSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";

/**
 * Persistent 280px sidebar (UI/UX Design Brief §11): logo, New Chat, session
 * history (Milestone 3), Analytics, Logout.
 */
export function Sidebar() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const activeId = params.get("s");

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["sessions"],
    queryFn: async () => {
      const t = await getToken();
      if (!t) throw new Error("Not authenticated");
      return api.listSessions(t);
    },
  });

  const del = useMutation({
    mutationFn: async (id: string) => {
      const t = await getToken();
      if (!t) throw new Error("Not authenticated");
      return api.deleteSession(t, id);
    },
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["sessions"] });
      if (id === activeId) router.push("/chat");
    },
  });

  return (
    <aside className="flex h-screen w-[280px] shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="px-4 py-5">
        <Link href="/home" className="text-lg font-semibold tracking-tight">
          Smart<span className="text-[var(--color-brand)]">DocZ</span>
        </Link>
      </div>

      <div className="px-3">
        <Button asChild className="w-full justify-start">
          <Link href="/chat">
            <Plus className="h-4 w-4" /> New chat
          </Link>
        </Button>
      </div>

      <nav className="mt-4 flex-1 overflow-y-auto px-3">
        <p className="px-2 pb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-muted)]">
          Recent
        </p>

        {isLoading ? (
          <div className="flex items-center gap-2 px-2 py-3 text-xs text-[var(--color-muted)]">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
          </div>
        ) : !sessions || sessions.length === 0 ? (
          <div className="rounded-[var(--radius)] border border-dashed border-[var(--color-border)] px-3 py-6 text-center text-xs text-[var(--color-muted)]">
            No conversations yet.
            <br />
            Start a new chat to begin.
          </div>
        ) : (
          <ul className="space-y-1">
            {sessions.map((s) => (
              <SessionItem
                key={s.id}
                session={s}
                active={s.id === activeId}
                deleting={del.isPending && del.variables === s.id}
                onOpen={() => router.push(`/chat?s=${s.id}`)}
                onDelete={() => del.mutate(s.id)}
              />
            ))}
          </ul>
        )}
      </nav>

      <div className="space-y-1 border-t border-[var(--color-border)] px-3 py-3">
        <Link
          href="/analytics"
          className="flex items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-sm text-[var(--color-muted)] transition-colors hover:bg-[#1d1d1d] hover:text-[var(--color-foreground)]"
        >
          <BarChart3 className="h-4 w-4" /> Analytics
        </Link>
        <SignOutButton redirectUrl="/login">
          <button className="flex w-full items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-sm text-[var(--color-muted)] transition-colors hover:bg-[#1d1d1d] hover:text-[var(--color-foreground)]">
            <LogOut className="h-4 w-4" /> Log out
          </button>
        </SignOutButton>
        {user && (
          <p className="truncate px-3 pt-2 text-xs text-[var(--color-muted)]">
            {user.primaryEmailAddress?.emailAddress ?? user.fullName}
          </p>
        )}
      </div>
    </aside>
  );
}

function SessionItem({
  session,
  active,
  deleting,
  onOpen,
  onDelete,
}: {
  session: ApiSessionSummary;
  active: boolean;
  deleting: boolean;
  onOpen: () => void;
  onDelete: () => void;
}) {
  return (
    <li
      className={cn(
        "group flex items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-sm transition-colors",
        active
          ? "bg-[#1d1d1d] text-[var(--color-foreground)]"
          : "text-[var(--color-muted)] hover:bg-[#1d1d1d] hover:text-[var(--color-foreground)]",
      )}
    >
      <button
        onClick={onOpen}
        className="flex min-w-0 flex-1 items-center gap-2 text-left"
      >
        <MessageSquare className="h-4 w-4 shrink-0" />
        <span className="truncate">{session.title || "Untitled chat"}</span>
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (confirm(`Delete “${session.title || "this chat"}”? This cannot be undone.`))
            onDelete();
        }}
        aria-label="Delete conversation"
        className="shrink-0 opacity-0 transition-opacity hover:text-[var(--color-error)] group-hover:opacity-100"
      >
        {deleting ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Trash2 className="h-3.5 w-3.5" />
        )}
      </button>
    </li>
  );
}
