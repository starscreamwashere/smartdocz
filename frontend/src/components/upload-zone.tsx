"use client";

import { useRef, useState } from "react";
import { Upload, Loader2, FileText, AlertCircle } from "lucide-react";

import { cn } from "@/lib/utils";

type UploadState = "idle" | "uploading" | "error";

export function UploadZone({
  onUpload,
  disabled,
}: {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}) {
  const [state, setState] = useState<UploadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setState("uploading");
    setError(null);
    try {
      await onUpload(file);
      setState("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setState("error");
    }
  }

  const busy = state === "uploading" || disabled;

  return (
    <div className="w-full max-w-xl">
      <div
        role="button"
        tabIndex={0}
        aria-disabled={busy}
        onClick={() => !busy && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !busy)
            inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (busy) return;
          const file = e.dataTransfer.files?.[0];
          if (file) void handleFile(file);
        }}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-[var(--radius)] border border-dashed px-6 py-12 text-center transition-colors",
          dragging
            ? "border-[var(--color-brand)] bg-[#16131f]"
            : "border-[var(--color-border)] bg-[var(--color-surface)]",
          busy ? "cursor-not-allowed opacity-70" : "cursor-pointer hover:border-[var(--color-brand)]",
        )}
      >
        {state === "uploading" ? (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-[var(--color-brand)]" />
            <p className="text-sm text-[var(--color-muted)]">
              Processing document…
            </p>
          </>
        ) : (
          <>
            <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-background)]">
              <Upload className="h-5 w-5 text-[var(--color-brand)]" />
            </div>
            <p className="text-sm font-medium">
              Drag and drop a PDF here, or click to upload
            </p>
            <p className="flex items-center gap-1.5 text-xs text-[var(--color-muted)]">
              <FileText className="h-3.5 w-3.5" /> PDF · up to 50 MB
            </p>
          </>
        )}
      </div>

      {state === "error" && error && (
        <p className="mt-3 flex items-center gap-2 text-sm text-[var(--color-error)]">
          <AlertCircle className="h-4 w-4 shrink-0" /> {error}
        </p>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
