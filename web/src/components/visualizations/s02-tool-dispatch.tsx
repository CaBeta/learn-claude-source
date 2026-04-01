"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const STEPS = [
  { label: "Register Tools", description: "Define tool schemas and handlers in dispatch map" },
  { label: "Receive Tool Call", description: "Model returns tool_use content block" },
  { label: "Lookup Handler", description: "Find handler function in dispatch map" },
  { label: "Validate Input", description: "Check input against tool schema" },
  { label: "Execute Handler", description: "Run the tool handler function" },
  { label: "Format Result", description: "Convert result to tool_result message" },
];

export function ToolDispatchVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(STEPS.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Tool Dispatch Visualization</h3>
        <StepControls {...viz} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {/* Tool registry */}
        <div className="col-span-1 rounded-lg border border-purple-300 bg-purple-50 p-3 dark:border-purple-700 dark:bg-purple-900/20">
          <div className="text-xs font-semibold text-purple-600 dark:text-purple-400 mb-2">Tool Registry</div>
          <div className="space-y-1">
            {["read_file", "write_file", "search", "bash"].map((tool, i) => (
              <motion.div
                key={tool}
                className={`rounded px-2 py-1 text-xs font-mono ${
                  viz.currentStep >= 2 && i === 0
                    ? "bg-purple-200 dark:bg-purple-800 text-purple-800 dark:text-purple-200"
                    : "bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400"
                }`}
                animate={{
                  scale: viz.currentStep >= 2 && i === 0 ? 1.05 : 1,
                }}
              >
                {tool}
              </motion.div>
            ))}
          </div>
        </div>
        {/* Pipeline */}
        <div className="col-span-2 space-y-2">
          {STEPS.map((step, i) => {
            const isActive = i === viz.currentStep;
            const isPast = i < viz.currentStep;
            return (
              <motion.div
                key={i}
                className={`rounded-lg border p-2 text-xs ${
                  isActive
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                    : isPast
                    ? "border-emerald-300 bg-emerald-50/50 dark:border-emerald-700 dark:bg-emerald-900/10"
                    : "border-zinc-200 dark:border-zinc-700"
                }`}
              >
                <span className="font-medium">{step.label}</span>
                <span className="ml-2 text-[var(--color-text-secondary)]">{step.description}</span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
