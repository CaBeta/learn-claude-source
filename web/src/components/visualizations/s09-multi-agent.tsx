"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const STAGES = [
  { label: "Receive Task", agent: "Coordinator" },
  { label: "Plan & Assign", agent: "Coordinator" },
  { label: "Execute Task A", agent: "Worker A" },
  { label: "Execute Task B", agent: "Worker B" },
  { label: "Collect Results", agent: "Coordinator" },
  { label: "Synthesize Response", agent: "Coordinator" },
];

export function MultiAgentVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(STAGES.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Multi-Agent Coordination</h3>
        <StepControls {...viz} />
      </div>
      <div className="relative">
        {/* Coordinator */}
        <div className="mb-4 rounded-lg border-2 border-emerald-500 bg-emerald-50 p-3 dark:bg-emerald-900/20">
          <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-1">Coordinator</div>
          <div className="flex gap-1">
            {STAGES.filter(s => s.agent === "Coordinator").map((s, i) => (
              <motion.div
                key={i}
                className={`rounded px-2 py-1 text-xs ${
                  STAGES.indexOf(s) === viz.currentStep
                    ? "bg-emerald-500 text-white"
                    : STAGES.indexOf(s) < viz.currentStep
                    ? "bg-emerald-200 dark:bg-emerald-800 text-emerald-800 dark:text-emerald-200"
                    : "bg-emerald-100 dark:bg-emerald-900 text-emerald-400"
                }`}
              >
                {s.label}
              </motion.div>
            ))}
          </div>
        </div>
        {/* Workers */}
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-blue-300 bg-blue-50 p-3 dark:border-blue-700 dark:bg-blue-900/20">
            <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-1">Worker A</div>
            <div className="text-xs text-[var(--color-text-secondary)]">
              {viz.currentStep >= 2 ? "Processing..." : "Idle"}
            </div>
            {viz.currentStep >= 4 && (
              <motion.span className="text-xs text-emerald-500" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                Complete
              </motion.span>
            )}
          </div>
          <div className="rounded-lg border border-purple-300 bg-purple-50 p-3 dark:border-purple-700 dark:bg-purple-900/20">
            <div className="text-xs font-semibold text-purple-600 dark:text-purple-400 mb-1">Worker B</div>
            <div className="text-xs text-[var(--color-text-secondary)]">
              {viz.currentStep >= 3 ? "Processing..." : "Idle"}
            </div>
            {viz.currentStep >= 4 && (
              <motion.span className="text-xs text-emerald-500" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                Complete
              </motion.span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
