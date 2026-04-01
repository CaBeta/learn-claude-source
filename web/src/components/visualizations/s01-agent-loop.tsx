"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const STEPS = [
  { label: "Start Loop", description: "while(true) begins the agent loop" },
  { label: "Call Model", description: "Send messages to the AI model via API" },
  { label: "Check Stop", description: "Is stop_reason == 'end_turn'?" },
  { label: "Parse Tools", description: "Extract tool_use content blocks" },
  { label: "Execute Tools", description: "Run each tool and collect results" },
  { label: "Append Results", description: "Add tool results to message history" },
  { label: "Loop Back", description: "Return to the top of the while loop" },
];

export function AgentLoopVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(STEPS.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Agent Loop Visualization</h3>
        <StepControls {...viz} />
      </div>
      <div className="relative">
        <div className="flex flex-col gap-3">
          {STEPS.map((step, i) => {
            const isActive = i === viz.currentStep;
            const isPast = i < viz.currentStep;
            return (
              <motion.div
                key={i}
                className={`flex items-center gap-4 rounded-lg border p-3 transition-all ${
                  isActive
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                    : isPast
                    ? "border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-900/10"
                    : "border-zinc-200 dark:border-zinc-700"
                }`}
                animate={{
                  scale: isActive ? 1.02 : 1,
                }}
              >
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                    isPast
                      ? "bg-emerald-500 text-white"
                      : isActive
                      ? "bg-blue-500 text-white"
                      : "bg-zinc-200 text-zinc-500 dark:bg-zinc-700"
                  }`}
                >
                  {i + 1}
                </div>
                <div>
                  <div className="text-sm font-medium">{step.label}</div>
                  <div className="text-xs text-[var(--color-text-secondary)]">
                    {step.description}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
        {/* Loop-back arrow indicator */}
        {viz.currentStep === STEPS.length - 1 && (
          <motion.div
            className="mt-3 text-center text-sm text-blue-500 font-medium"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            Loop back to step 1
          </motion.div>
        )}
      </div>
    </div>
  );
}
