"use client";

import { Suspense, lazy } from "react";
import { DocRenderer } from "@/components/docs/doc-renderer";
import { SourceViewer } from "@/components/code/source-viewer";
import { ExecutionFlow } from "@/components/architecture/execution-flow";
import { ArchDiagram } from "@/components/architecture/arch-diagram";
import { DesignDecisions } from "@/components/architecture/design-decisions";
import { WhatsNew } from "@/components/diff/whats-new";
import { Tabs } from "@/components/ui/tabs";
import { AgentLoopSimulator } from "@/components/simulator/agent-loop-simulator";

// Lazy load the session visualization
const SessionVisualization = lazy(() =>
  import("@/components/visualizations/index").then((m) => ({ default: m.SessionVisualization }))
);

interface VersionDetailClientProps {
  version: string;
  diff: {
    from: string;
    to: string;
    newClasses: string[];
    newFunctions: string[];
    newTools: string[];
    locDelta: number;
  } | null;
  source: string;
  filename: string;
}

export function VersionDetailClient({
  version,
  diff,
  source,
  filename,
}: VersionDetailClientProps) {
  const tabs = [
    { id: "learn", label: "学习" },
    { id: "simulate", label: "模拟" },
    { id: "code", label: "代码" },
    { id: "deep-dive", label: "深入" },
  ];

  return (
    <div className="space-y-6">
      {/* Visualization Hero */}
      <Suspense
        fallback={
          <div className="rounded-lg border border-[var(--color-border)] bg-zinc-50 p-8 text-center dark:bg-zinc-800/50">
            <p className="text-sm text-[var(--color-text-secondary)]">Loading visualization...</p>
          </div>
        }
      >
        <SessionVisualization version={version} />
      </Suspense>

      <Tabs tabs={tabs} defaultTab="learn">
        {(activeTab) => (
          <>
            {activeTab === "learn" && <DocRenderer version={version} />}
            {activeTab === "simulate" && <AgentLoopSimulator version={version} />}
            {activeTab === "code" && (
              <SourceViewer source={source} filename={filename} />
            )}
            {activeTab === "deep-dive" && (
              <div className="space-y-8">
                <ExecutionFlow version={version} />
                <ArchDiagram version={version} />
                {diff && <WhatsNew diff={diff} />}
                <DesignDecisions version={version} />
              </div>
            )}
          </>
        )}
      </Tabs>
    </div>
  );
}
