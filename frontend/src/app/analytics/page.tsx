import { BarChart3 } from "lucide-react";

// Analytics dashboard — RAGAS evaluation arrives in Milestone 6.
// Until then we show the documented empty state (App Flow, Empty State 3).
export default function AnalyticsPage() {
  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-[var(--color-border)] px-6 py-4">
        <h1 className="text-lg font-semibold">Analytics</h1>
      </header>
      <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]">
          <BarChart3 className="h-6 w-6 text-[var(--color-brand)]" />
        </div>
        <h2 className="mt-5 text-xl font-semibold">No evaluations yet</h2>
        <p className="mt-2 max-w-md text-sm text-[var(--color-muted)]">
          Evaluate an answer to see quality metrics — faithfulness, answer
          relevancy, and context precision. The RAGAS dashboard ships in
          Milestone 6.
        </p>
      </div>
    </div>
  );
}
