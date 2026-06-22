import Link from "next/link";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import { FileText, Sparkles, BarChart3, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";

const FORMATS = ["PDF", "DOCX", "TXT", "CSV", "JSON", "YouTube"];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6">
      {/* Top bar */}
      <header className="flex items-center justify-between py-6">
        <span className="text-lg font-semibold tracking-tight">
          Smart<span className="text-[var(--color-brand)]">DocZ</span>
        </span>
        <div className="flex items-center gap-2">
          <SignedOut>
            <Button asChild variant="ghost" size="sm">
              <Link href="/sign-in">Log in</Link>
            </Button>
            <Button asChild size="sm">
              <Link href="/sign-up">Get started</Link>
            </Button>
          </SignedOut>
          <SignedIn>
            <Button asChild size="sm">
              <Link href="/chat">Open workspace</Link>
            </Button>
          </SignedIn>
        </div>
      </header>

      {/* Hero */}
      <section className="flex flex-1 flex-col items-center justify-center py-20 text-center">
        <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-xs text-[var(--color-muted)]">
          <Sparkles className="h-3.5 w-3.5 text-[var(--color-brand)]" />
          AI-powered document intelligence
        </span>
        <h1 className="max-w-2xl text-5xl font-bold leading-tight tracking-tight">
          Chat with your documents.
          <br />
          Get answers instantly.
        </h1>
        <p className="mt-5 max-w-xl text-lg text-[var(--color-muted)]">
          Upload a document and ask questions in plain language. SmartDocZ
          retrieves the right context, answers with citations, and lets you
          evaluate answer quality.
        </p>

        <div className="mt-8 flex items-center gap-3">
          <SignedOut>
            <Button asChild size="lg">
              <Link href="/sign-up">
                Get started <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="secondary" size="lg">
              <Link href="/sign-in">Learn more</Link>
            </Button>
          </SignedOut>
          <SignedIn>
            <Button asChild size="lg">
              <Link href="/chat">
                Go to workspace <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </SignedIn>
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-2">
          {FORMATS.map((f) => (
            <span
              key={f}
              className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 font-mono text-xs text-[var(--color-muted)]"
            >
              {f}
            </span>
          ))}
        </div>
      </section>

      {/* Supporting features */}
      <section className="grid gap-4 pb-24 sm:grid-cols-3">
        <Feature
          icon={<FileText className="h-5 w-5 text-[var(--color-brand)]" />}
          title="Multi-format ingestion"
          body="PDFs, DOCX, spreadsheets, JSON, and YouTube transcripts — one unified interface."
        />
        <Feature
          icon={<Sparkles className="h-5 w-5 text-[var(--color-brand)]" />}
          title="Grounded answers"
          body="Retrieval-augmented responses cite the source so you can trust every answer."
        />
        <Feature
          icon={<BarChart3 className="h-5 w-5 text-[var(--color-brand)]" />}
          title="Quality analytics"
          body="Evaluate faithfulness, relevancy, and context precision with RAGAS metrics."
        />
      </section>
    </main>
  );
}

function Feature({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="mb-3">{icon}</div>
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-1.5 text-sm text-[var(--color-muted)]">{body}</p>
    </div>
  );
}
