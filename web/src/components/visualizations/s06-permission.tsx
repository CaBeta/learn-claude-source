"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const MODES = [
  { name: "Auto Approve", level: 0, desc: "Safe read operations", color: "bg-emerald-500" },
  { name: "Auto Deny", level: 1, desc: "Dangerous operations blocked", color: "bg-red-500" },
  { name: "Ask Once", level: 2, desc: "Ask user once per tool", color: "bg-amber-500" },
  { name: "Ask Always", level: 3, desc: "Ask every invocation", color: "bg-orange-500" },
  { name: "Allow List", level: 4, desc: "Pre-approved tool list", color: "bg-blue-500" },
  { name: "Deny List", level: 5, desc: "Blocked tool list", color: "bg-purple-500" },
];

export function PermissionVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(MODES.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Permission Modes</h3>
        <StepControls {...viz} />
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {MODES.map((mode, i) => {
          const isActive = i === viz.currentStep;
          const isPast = i < viz.currentStep;
          return (
            <motion.div
              key={i}
              className={`rounded-lg border p-3 text-center transition-all ${
                isActive
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-300"
                  : isPast
                  ? "border-zinc-300 dark:border-zinc-600 opacity-70"
                  : "border-zinc-200 dark:border-zinc-700"
              }`}
              animate={{ scale: isActive ? 1.05 : 1 }}
            >
              <div className={`mx-auto mb-2 h-3 w-3 rounded-full ${mode.color}`} />
              <div className="text-xs font-semibold">{mode.name}</div>
              <div className="text-xs text-[var(--color-text-secondary)] mt-1">{mode.desc}</div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
