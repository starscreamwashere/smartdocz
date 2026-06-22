"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { Upload, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

import { api, type ApiUser } from "@/lib/api";

export default function ChatPage() {
  const { getToken } = useAuth();

  // Milestone 1 proof: the protected page calls the protected /me endpoint with
  // the Clerk token, confirming the full auth handshake works end to end.
  const { data, isLoading, isError, error } = useQuery<ApiUser>({
    queryKey: ["me"],
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("No session token");
      return api.me(token);
    },
  });

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
        <h1 className="text-lg font-semibold">Workspace</h1>
        <BackendStatus
          isLoading={isLoading}
          isError={isError}
          error={error}
          user={data}
        />
      </header>

      {/* Empty state — App Flow Empty State 2: no uploaded files yet */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]">
          <Upload className="h-6 w-6 text-[var(--color-brand)]" />
        </div>
        <h2 className="mt-5 text-xl font-semibold">
          Upload a document to begin chatting
        </h2>
        <p className="mt-2 max-w-md text-sm text-[var(--color-muted)]">
          Drag &amp; drop a PDF, DOCX, TXT, CSV, JSON file or paste a YouTube URL.
          Uploading and chat arrive in Milestone 2 — auth and the app shell are
          ready now.
        </p>
        <div className="mt-6 w-full max-w-md rounded-[var(--radius)] border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-10 text-sm text-[var(--color-muted)]">
          Drag and drop files here or click to upload
        </div>
      </div>
    </div>
  );
}

function BackendStatus({
  isLoading,
  isError,
  error,
  user,
}: {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  user?: ApiUser;
}) {
  if (isLoading) {
    return (
      <span className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Connecting to backend…
      </span>
    );
  }
  if (isError) {
    return (
      <span className="flex items-center gap-2 text-xs text-[var(--color-error)]">
        <AlertCircle className="h-3.5 w-3.5" />
        {error instanceof Error ? error.message : "Backend unreachable"}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-2 text-xs text-[var(--color-success)]">
      <CheckCircle2 className="h-3.5 w-3.5" />
      Authenticated as {user?.email ?? user?.clerk_user_id}
    </span>
  );
}
