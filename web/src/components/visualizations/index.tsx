"use client";
import React, { Suspense, lazy } from "react";

interface SessionVisualizationProps {
  version: string;
}

// Lazy-loaded visualization components for each session
const visualizationMap: Record<string, React.LazyExoticComponent<{ version: string }>> = {
  s01: lazy(() => import("./s01-agent-loop").then((m) => ({ default: m.AgentLoopVisualization }))),
  s02: lazy(() => import("./s02-tool-dispatch").then((m) => ({ default: m.ToolDispatchVisualization }))),
  s03: lazy(() => import("./s03-streaming").then((m) => ({ default: m.StreamingVisualization }))),
  s04: lazy(() => import("./s04-subagent").then((m) => ({ default: m.SubAgentVisualization }))),
  s05: lazy(() => import("./s05-context-compact").then((m) => ({ default: m.ContextCompactVisualization }))),
  s06: lazy(() => import("./s06-permission").then((m) => ({ default: m.PermissionVisualization }))),
  s07: lazy(() => import("./s07-skills").then((m) => ({ default: m.SkillsVisualization }))),
  s08: lazy(() => import("./s08-hooks").then((m) => ({ default: m.HooksVisualization }))),
  s09: lazy(() => import("./s09-multi-agent").then((m) => ({ default: m.MultiAgentVisualization }))),
  s10: lazy(() => import("./s10-background-tasks").then((m) => ({ default: m.BackgroundTasksVisualization }))),
  s11: lazy(() => import("./s11-session-memory").then((m) => ({ default: m.SessionMemoryVisualization }))),
  s12: lazy(() => import("./s12-production").then((m) => ({ default: m.ProductionVisualization }))),
};

function VisualizationFallback() {
  return (
    <div className="flex items-center justify-center rounded-lg border border-[var(--color-border)] bg-zinc-50 p-8 dark:bg-zinc-800/50">
      <div className="text-sm text-[var(--color-text-secondary)]">
        Loading visualization...
      </div>
    </div>
  );
}

export function SessionVisualization({ version }: SessionVisualizationProps) {
  const Component = visualizationMap[version];

  if (!Component) {
    return (
      <div className="rounded-lg border border-[var(--color-border)] bg-zinc-50 p-8 text-center dark:bg-zinc-800/50">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Interactive visualization for {version}
        </p>
      </div>
    );
  }

  return (
    <Suspense fallback={<VisualizationFallback />}>
      <Component version={version} />
    </Suspense>
  );
}
