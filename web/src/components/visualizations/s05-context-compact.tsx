"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const LAYERS = [
  { name: "Sliding Window", desc: "Keep recent N messages", color: "bg-blue-500" },
  { name: "Summarization", desc: "Compress old messages to summary", color: "bg-emerald-500" },
  { name: "Tool Result Truncation", desc: "Truncate large tool outputs", color: "bg-amber-500" },
  { name: "Deduplication", desc: "Remove duplicate messages", color: "bg-purple-500" },
  { name: "Relevance Filter", desc: "Keep only relevant context", color: "bg-rose-500" },
];

export function ContextCompactVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(LAYERS.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Context Compression Pipeline</h3>
        <StepControls {...viz} />
      </div>
      <div className="space-y-2">
        {LAYERS.map((layer, i) => {
          const isActive = i === viz.currentStep;
          const isPast = i < viz.currentStep;
          return (
            <motion.div
              key={i}
              className={`flex items-center gap-3 rounded-lg border p-3 ${
                isActive ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20" :
                isPast ? "border-emerald-300 dark:border-emerald-700 opacity-60" :
                "border-zinc-200 dark:border-zinc-700"
              }`}
              animate={{ scale: isActive ? 1.01 : 1 }}
            >
              <div className={`h-3 w-3 rounded-full ${layer.color} ${isPast ? "opacity-50" : ""}`} />
              <div className="flex-1">
                <div className="text-sm font-medium">{layer.name}</div>
                <div className="text-xs text-[var(--color-text-secondary)]">{layer.desc}</div>
              </div>
              {isPast && (
                <span className="text-xs text-emerald-500 font-medium">Compressed</span>
              )}
              {isActive && (
                <span className="text-xs text-blue-500 font-medium animate-pulse">Processing...</span>
              )}
            </motion.div>
          );
        })}
      </div>
      {viz.currentStep >= LAYERS.length - 1 && (
        <motion.div className="text-center text-sm text-emerald-500 font-medium" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          Context compressed and ready for model
        </motion.div>
      )}
    </div>
  );
}
