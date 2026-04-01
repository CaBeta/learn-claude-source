"use client";
import { useState } from "react";

interface SourceViewerProps {
  source: string;
  filename: string;
}

export function SourceViewer({ source, filename }: SourceViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(source);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--color-border)]">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-zinc-50 px-4 py-2 dark:bg-zinc-800/50">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-red-500/70" />
          <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
          <span className="h-3 w-3 rounded-full bg-green-500/70" />
          <span className="ml-3 text-xs text-[var(--color-text-secondary)] font-mono">
            agents/{filename}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="max-h-[600px] overflow-auto bg-zinc-950 p-4 text-sm leading-relaxed text-zinc-300">
        <code>{source}</code>
      </pre>
    </div>
  );
}
