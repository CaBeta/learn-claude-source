"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const STAGES = [
  { label: "Skill Definition", desc: "Define skill template with parameters" },
  { label: "Registration", desc: "Register skill in SkillManager" },
  { label: "Matching", desc: "Match user intent to skill" },
  { label: "Loading", desc: "Load and instantiate skill" },
  { label: "Execution", desc: "Execute skill with parameters" },
];

export function SkillsVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(STAGES.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Skill Loading Pipeline</h3>
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
                  ? "border-amber-500 bg-amber-50 dark:bg-amber-900/20"
                  : isPast
                  ? "border-emerald-300 dark:border-emerald-700 opacity-60"
                  : "border-zinc-200 dark:border-zinc-700"
              }`}
            >
              <div className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                isPast ? "bg-emerald-500 text-white" : isActive ? "bg-amber-500 text-white" : "bg-zinc-200 text-zinc-500 dark:bg-zinc-700"
              }`}>
                {i + 1}
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
