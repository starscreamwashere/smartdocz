"use client";

import { useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Loader2, CheckCircle2 } from "lucide-react";

import {
  api,
  METRIC_TARGETS,
  type AnalyticsResult,
  type ApiMessage,
} from "@/lib/api";
import { Button } from "@/components/ui/button";

type Metric = keyof typeof METRIC_TARGETS;
const METRIC_LABELS: Record<Metric, string> = {
  faithfulness: "Faithfulness",
  answer_relevancy: "Answer Relevancy",
  context_precision: "Context Precision",
};

export default function AnalyticsPage() {
  const { getToken } = useAuth();
  const qc = useQueryClient();
  const token = async () => {
    const t = await getToken();
    if (!t) throw new Error("Not authenticated");
    return t;
  };

  const [sessionId, setSessionId] = useState<string>("");
  const [messageId, setMessageId] = useState<string>("");
  const [reference, setReference] = useState("");

  const { data: sessions } = useQuery({
    queryKey: ["sessions"],
    queryFn: async () => api.listSessions(await token()),
  });

  const { data: messages } = useQuery({
    queryKey: ["messages", sessionId],
    queryFn: async () => api.messages(await token(), sessionId),
    enabled: !!sessionId,
  });

  const { data: history } = useQuery({
    queryKey: ["analytics", sessionId],
    queryFn: async () => api.getAnalytics(await token(), sessionId),
    enabled: !!sessionId,
  });

  // Pair each assistant answer with the question that preceded it.
  const answers = useMemo(() => {
    const pairs: { id: string; question: string; answer: string }[] = [];
    let lastUser = "";
    for (const m of (messages ?? []) as ApiMessage[]) {
      if (m.role === "user") lastUser = m.content;
      else if (m.role === "assistant") pairs.push({ id: m.id, question: lastUser, answer: m.content });
    }
    return pairs;
  }, [messages]);

  const selected = answers.find((a) => a.id === messageId);

  const evaluate = useMutation({
    mutationFn: async () => api.evaluate(await token(), messageId, reference),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics", sessionId] }),
  });

  const latest = evaluate.data;

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-[var(--color-border)] px-6 py-4">
        <h1 className="text-lg font-semibold">Analytics</h1>
        <p className="text-xs text-[var(--color-muted)]">
          Evaluate answer quality with RAGAS-style metrics.
        </p>
      </header>

      {!sessions || sessions.length === 0 ? (
        <EmptyState text="No conversations yet. Chat with a document first, then evaluate its answers here." />
      ) : (
        <div className="mx-auto w-full max-w-3xl flex-1 overflow-y-auto px-6 py-6">
          {/* Step 1 — pick a session */}
          <Label>Conversation</Label>
          <select
            value={sessionId}
            onChange={(e) => {
              setSessionId(e.target.value);
              setMessageId("");
              evaluate.reset();
            }}
            className="mb-5 w-full rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm outline-none focus:border-[var(--color-brand)]"
          >
            <option value="">Select a conversation…</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title || "Untitled chat"} ({s.message_count} messages)
              </option>
            ))}
          </select>

          {/* Step 2 — pick an answer */}
          {sessionId && (
            <>
              <Label>Answer to evaluate</Label>
              {answers.length === 0 ? (
                <p className="mb-5 rounded-[var(--radius)] border border-dashed border-[var(--color-border)] px-3 py-4 text-sm text-[var(--color-muted)]">
                  This conversation has no answers yet.
                </p>
              ) : (
                <div className="mb-5 space-y-2">
                  {answers.map((a, i) => (
                    <button
                      key={a.id}
                      onClick={() => {
                        setMessageId(a.id);
                        evaluate.reset();
                      }}
                      className={`block w-full rounded-[var(--radius)] border px-3 py-2.5 text-left text-sm transition-colors ${
                        messageId === a.id
                          ? "border-[var(--color-brand)] bg-[#16131f]"
                          : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-brand)]"
                      }`}
                    >
                      <span className="text-[var(--color-muted)]">Q{i + 1}: </span>
                      {a.question || "(question unavailable)"}
                      <span className="mt-1 block truncate text-xs text-[var(--color-muted)]">
                        → {a.answer}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Step 3 — reference + evaluate */}
          {selected && (
            <>
              <Label>Reference answer</Label>
              <textarea
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                rows={3}
                placeholder="Paste the ideal/expected answer to compare against…"
                className="mb-3 w-full resize-y rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm outline-none placeholder:text-[var(--color-muted)] focus:border-[var(--color-brand)]"
              />
              <Button
                onClick={() => evaluate.mutate()}
                disabled={evaluate.isPending || !reference.trim()}
              >
                {evaluate.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Evaluating…
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" /> Evaluate answer
                  </>
                )}
              </Button>
              {evaluate.isError && (
                <p className="mt-3 text-sm text-[var(--color-error)]">
                  {(evaluate.error as Error).message}
                </p>
              )}

              {latest && (
                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  {(Object.keys(METRIC_LABELS) as Metric[]).map((m) => (
                    <MetricCard key={m} metric={m} value={latest[m] ?? 0} />
                  ))}
                </div>
              )}
            </>
          )}

          {/* Past evaluations */}
          {sessionId && history && history.length > 0 && (
            <div className="mt-8">
              <Label>Past evaluations</Label>
              <div className="overflow-hidden rounded-[var(--radius)] border border-[var(--color-border)]">
                <table className="w-full text-sm">
                  <thead className="bg-[var(--color-surface)] text-xs text-[var(--color-muted)]">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">When</th>
                      <th className="px-3 py-2 text-right font-medium">Faith.</th>
                      <th className="px-3 py-2 text-right font-medium">Relev.</th>
                      <th className="px-3 py-2 text-right font-medium">Precision</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((r: AnalyticsResult) => (
                      <tr key={r.id} className="border-t border-[var(--color-border)]">
                        <td className="px-3 py-2 text-[var(--color-muted)]">
                          {new Date(r.created_at).toLocaleString()}
                        </td>
                        <ScoreCell value={r.faithfulness} metric="faithfulness" />
                        <ScoreCell value={r.answer_relevancy} metric="answer_relevancy" />
                        <ScoreCell value={r.context_precision} metric="context_precision" />
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function metricColor(value: number, target: number): string {
  if (value >= target) return "var(--color-success)";
  if (value >= target - 0.1) return "var(--color-warning)";
  return "var(--color-error)";
}

function MetricCard({ metric, value }: { metric: Metric; value: number }) {
  const target = METRIC_TARGETS[metric];
  const color = metricColor(value, target);
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p className="text-xs text-[var(--color-muted)]">{METRIC_LABELS[metric]}</p>
      <p className="mt-1 font-mono text-3xl font-semibold" style={{ color }}>
        {value.toFixed(2)}
      </p>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#262626]">
        <div className="h-full rounded-full" style={{ width: `${value * 100}%`, background: color }} />
      </div>
      <p className="mt-1.5 text-[11px] text-[var(--color-muted)]">target ≥ {target.toFixed(2)}</p>
    </div>
  );
}

function ScoreCell({ value, metric }: { value: number | null; metric: Metric }) {
  const v = value ?? 0;
  return (
    <td className="px-3 py-2 text-right font-mono" style={{ color: metricColor(v, METRIC_TARGETS[metric]) }}>
      {v.toFixed(2)}
    </td>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-[var(--color-muted)]">
      {children}
    </p>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]">
        <BarChart3 className="h-6 w-6 text-[var(--color-brand)]" />
      </div>
      <p className="mt-5 max-w-md text-sm text-[var(--color-muted)]">{text}</p>
    </div>
  );
}
