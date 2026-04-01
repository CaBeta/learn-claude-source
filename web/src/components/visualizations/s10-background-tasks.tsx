"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const TASK_STAGES = [
  { label: "Task Created", status: "pending", thread: "main" },
  { label: "Queued", status: "pending", thread: "main" },
  { label: "Thread Spawned", status: "running", thread: "background" },
  { label: "Executing...", status: "running", thread: "background" },
  { label: "Complete", status: "completed", thread: "background" },
  { label: "Result Delivered", status: "completed", thread: "main" },
];

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-amber-500",
  running: "bg-blue-500 animate-pulse",
  completed: "bg-emerald-500",
};

export function BackgroundTasksVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(TASK_STAGES.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Background Task Execution</h3>
        <StepControls {...viz} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        {/* Main thread */}
        <div className="rounded-lg border border-zinc-300 p-3 dark:border-zinc-600">
          <div className="text-xs font-semibold mb-2">Main Thread</div>
          <div className="space-y-1">
            {TASK_STAGES.filter(s => s.thread === "main").map((stage, i) => {
              const allStagesIdx = TASK_STAGES.indexOf(stage);
              const isActive = allStagesIdx === viz.currentStep;
              return (
                <motion.div
                  key={i}
                  className={`rounded px-2 py-1 text-xs ${
                    isActive ? "bg-blue-100 dark:bg-blue-900" : allStagesIdx < viz.currentStep ? "bg-zinc-100 dark:bg-zinc-800" : ""
                  }`}
                  animate={{ scale: isActive ? 1.05 : 1 }}
                >
                  {stage.label}
                </motion.div>
              );
            })}
          </div>
        </div>
        {/* Background thread */}
        <div className="rounded-lg border border-purple-300 bg-purple-50 p-3 dark:border-purple-700 dark:bg-purple-900/20">
          <div className="text-xs font-semibold mb-2">Background Thread</div>
          <div className="space-y-1">
            {TASK_STAGES.filter(s => s.thread === "background").map((stage, i) => {
              const allStagesIdx = TASK_STAGES.indexOf(stage);
              const isActive = allStagesIdx === viz.currentStep;
              return (
                <motion.div
                  key={i}
                  className={`flex items-center gap-2 rounded px-2 py-1 text-xs ${
                    isActive ? "bg-purple-200 dark:bg-purple-800" : allStagesIdx < viz.currentStep ? "bg-purple-100 dark:bg-purple-900" : ""
                  }`}
                >
                  <div className={`h-2 w-2 rounded-full ${STATUS_COLORS[stage.status]}`} />
                  {stage.label}
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
