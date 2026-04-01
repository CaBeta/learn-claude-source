"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

export function SubAgentVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(5);

  const stages = [
    { label: "Parent receives task", desc: "User sends complex task to parent agent" },
    { label: "Decompose task", desc: "Parent breaks task into subtasks" },
    { label: "Spawn SubAgents", desc: "Create isolated child agents with subtasks" },
    { label: "Collect results", desc: "SubAgents complete and return results" },
    { label: "Synthesize", desc: "Parent combines subagent results into final response" },
  ];

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">SubAgent Delegation</h3>
        <StepControls {...viz} />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <motion.div
          className={`rounded-lg border p-4 text-center ${
            viz.currentStep >= 2 ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20" : "border-zinc-200 dark:border-zinc-700"
          }`}
          animate={{ scale: viz.currentStep >= 2 ? 1.02 : 1 }}
        >
          <div className="text-xs font-semibold mb-1">SubAgent A</div>
          <div className="text-xs text-[var(--color-text-secondary)]">
            {viz.currentStep >= 2 ? "Processing..." : "Waiting"}
          </div>
          {viz.currentStep >= 3 && (
            <motion.div className="mt-2 text-xs text-emerald-500 font-medium" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              Done
            </motion.div>
          )}
        </motion.div>
        <div className="rounded-lg border border-emerald-500 bg-emerald-50 p-4 text-center dark:bg-emerald-900/20">
          <div className="text-xs font-semibold mb-1">Parent Agent</div>
          <div className="text-xs text-[var(--color-text-secondary)]">
            {stages[viz.currentStep]?.label}
          </div>
        </div>
        <motion.div
          className={`rounded-lg border p-4 text-center ${
            viz.currentStep >= 2 ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20" : "border-zinc-200 dark:border-zinc-700"
          }`}
          animate={{ scale: viz.currentStep >= 2 ? 1.02 : 1 }}
        >
          <div className="text-xs font-semibold mb-1">SubAgent B</div>
          <div className="text-xs text-[var(--color-text-secondary)]">
            {viz.currentStep >= 2 ? "Processing..." : "Waiting"}
          </div>
          {viz.currentStep >= 3 && (
            <motion.div className="mt-2 text-xs text-emerald-500 font-medium" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              Done
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
