"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignOutButton, useUser } from "@clerk/nextjs";
import { Plus, MessageSquare, BarChart3, LogOut } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

/**
 * Persistent 280px left sidebar (UI/UX Design Brief §11).
 * Contents: logo · New Chat · session history · Analytics · Logout.
 *
 * Session history is a placeholder until Milestone 3 (Session Persistence).
 */
export function Sidebar() {
  const pathname = usePathname();
  const { user } = useUser();

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

      {/* Chat history — populated in Milestone 3 */}
      <nav className="mt-4 flex-1 overflow-y-auto px-3">
        <p className="px-2 pb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-muted)]">
          Recent
        </p>
        <div className="rounded-[var(--radius)] border border-dashed border-[var(--color-border)] px-3 py-6 text-center text-xs text-[var(--color-muted)]">
          No conversations yet.
          <br />
          Start a new chat to begin.
        </div>
      </nav>

      <div className="space-y-1 border-t border-[var(--color-border)] px-3 py-3">
        <NavLink
          href="/analytics"
          active={pathname.startsWith("/analytics")}
          icon={<BarChart3 className="h-4 w-4" />}
          label="Analytics"
        />
        <NavLink
          href="/chat"
          active={pathname.startsWith("/chat")}
          icon={<MessageSquare className="h-4 w-4" />}
          label="Chat"
        />
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

function NavLink({
  href,
  active,
  icon,
  label,
}: {
  href: string;
  active: boolean;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-sm transition-colors",
        active
          ? "bg-[#1d1d1d] text-[var(--color-foreground)]"
          : "text-[var(--color-muted)] hover:bg-[#1d1d1d] hover:text-[var(--color-foreground)]",
      )}
    >
      {icon}
      {label}
    </Link>
  );
}
