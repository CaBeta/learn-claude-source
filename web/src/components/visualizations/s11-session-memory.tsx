"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const STAGES = [
  { label: "Session Start", desc: "Load previous session state" },
  { label: "Memory Lookup", desc: "Search for relevant memories" },
  { label: "Working Memory", desc: "Active facts and preferences" },
  { label: "Store Memory", desc: "Save new learnings to memory file" },
  { label: "Session End", desc: "Persist session state to disk" },
];

export function SessionMemoryVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(STAGES.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Session Memory</h3>
        <StepControls {...viz} />
      </div>
      <div className="space-y-2">
        {STAGES.map((stage, i) => {
          const isActive = i === viz.currentStep;
          const isPast = i < viz.currentStep;
          return (
            <motion.div
              key={i}
              className={`flex items-center gap-3 rounded-lg border p-3 ${
                isActive
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                  : isPast
                  ? "border-emerald-300 dark:border-emerald-700"
                  : "border-zinc-200 dark:border-zinc-700"
              }`}
            >
              <div className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                isPast ? "bg-emerald-500 text-white" : isActive ? "bg-blue-500 text-white" : "bg-zinc-200 dark:bg-zinc-700"
              }`}>
                {isPast ? "OK" : i + 1}
              </div>
              <div>
                <div className="text-sm font-medium">{stage.label}</div>
                <div className="text-xs text-[var(--color-text-secondary)]">{stage.desc}</div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
