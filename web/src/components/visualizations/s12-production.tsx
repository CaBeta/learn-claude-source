"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const SYSTEMS = [
  { name: "Agent Loop", status: "running", color: "bg-blue-500" },
  { name: "Tool Dispatch", status: "running", color: "bg-purple-500" },
  { name: "Streaming", status: "running", color: "bg-emerald-500" },
  { name: "SubAgents", status: "running", color: "bg-amber-500" },
  { name: "Context Mgmt", status: "running", color: "bg-rose-500" },
  { name: "Permissions", status: "running", color: "bg-orange-500" },
  { name: "Skills", status: "running", color: "bg-teal-500" },
  { name: "Hooks", status: "running", color: "bg-indigo-500" },
  { name: "Background Tasks", status: "running", color: "bg-cyan-500" },
  { name: "Session Memory", status: "running", color: "bg-pink-500" },
];

export function ProductionVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(SYSTEMS.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Production Agent - All Systems</h3>
        <StepControls {...viz} />
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {SYSTEMS.map((sys, i) => {
          const isActive = i === viz.currentStep;
          const isPast = i < viz.currentStep;
          return (
            <motion.div
              key={i}
              className={`rounded-lg border p-3 text-center ${
                isActive
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-300"
                  : isPast
                  ? "border-emerald-300 dark:border-emerald-700"
                  : "border-zinc-200 dark:border-zinc-700"
              }`}
              animate={{ scale: isActive ? 1.08 : 1 }}
            >
              <div className={`mx-auto mb-2 h-3 w-3 rounded-full ${isPast ? "bg-emerald-500" : sys.color}`} />
              <div className="text-xs font-medium">{sys.name}</div>
              <div className={`text-xs mt-1 ${
                isPast ? "text-emerald-500" : isActive ? "text-blue-500 animate-pulse" : "text-zinc-400"
              }`}>
                {isPast ? "Active" : isActive ? "Starting..." : "Standby"}
              </div>
            </motion.div>
          );
        })}
      </div>
      {viz.currentStep >= SYSTEMS.length - 1 && (
        <motion.div
          className="text-center text-sm font-semibold text-emerald-500"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          All systems operational - Production Agent ready
        </motion.div>
      )}
    </div>
  );
}
