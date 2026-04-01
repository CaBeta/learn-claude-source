"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const HOOK_POINTS = [
  { point: "Session Start", hooks: ["initialize_state"], color: "bg-emerald-500" },
  { point: "Before Model Call", hooks: ["check_context", "inject_system"], color: "bg-blue-500" },
  { point: "After Model Call", hooks: ["log_response", "check_safety"], color: "bg-purple-500" },
  { point: "Before Tool Call", hooks: ["validate_input", "check_permission"], color: "bg-amber-500" },
  { point: "After Tool Call", hooks: ["log_result", "transform_output"], color: "bg-rose-500" },
  { point: "Session End", hooks: ["save_state", "cleanup"], color: "bg-zinc-500" },
];

export function HooksVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(HOOK_POINTS.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Lifecycle Hook Points</h3>
        <StepControls {...viz} />
      </div>
      <div className="space-y-2">
        {HOOK_POINTS.map((hp, i) => {
          const isActive = i === viz.currentStep;
          const isPast = i < viz.currentStep;
          return (
            <motion.div
              key={i}
              className={`rounded-lg border p-3 ${
                isActive
                  ? "border-amber-500 bg-amber-50 dark:bg-amber-900/20"
                  : isPast
                  ? "border-zinc-300 dark:border-zinc-600"
                  : "border-zinc-200 dark:border-zinc-700"
              }`}
              animate={{ scale: isActive ? 1.02 : 1 }}
            >
              <div className="flex items-center gap-2 mb-1">
                <div className={`h-2 w-2 rounded-full ${hp.color}`} />
                <span className="text-sm font-medium">{hp.point}</span>
              </div>
              <div className="flex flex-wrap gap-1 ml-4">
                {hp.hooks.map((hook) => (
                  <span key={hook} className={`rounded px-1.5 py-0.5 text-xs font-mono ${
                    isActive ? "bg-amber-200 dark:bg-amber-800" : "bg-zinc-100 dark:bg-zinc-800"
                  }`}>
                    {hook}
                  </span>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
