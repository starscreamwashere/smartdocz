import { Suspense } from "react";

import { Sidebar } from "@/components/sidebar";

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Suspense fallback={<div className="w-[280px] shrink-0 border-r border-[var(--color-border)] bg-[var(--color-surface)]" />}>
        <Sidebar />
      </Suspense>
      <div className="flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}
