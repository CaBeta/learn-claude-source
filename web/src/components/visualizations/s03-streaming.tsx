"use client";
import { motion } from "framer-motion";
import { useSteppedVisualization } from "@/hooks/useSteppedVisualization";
import { StepControls } from "./shared/step-controls";

const STREAM_TOKENS = [
  "The", " architecture", " follows", " a", " layered", " approach", " where", " each",
  " layer", " adds", " new", " capabilities", " to", " the", " agent", ".",
];

export function StreamingVisualization({ version }: { version: string }) {
  const viz = useSteppedVisualization(STREAM_TOKENS.length);

  return (
    <div className="space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Streaming Visualization</h3>
        <StepControls {...viz} />
      </div>
      <div className="rounded-lg border border-[var(--color-border)] bg-zinc-50 p-4 dark:bg-zinc-800/50">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs text-[var(--color-text-secondary)]">Streaming response...</span>
        </div>
        <div className="min-h-[60px] font-mono text-sm">
          {STREAM_TOKENS.map((token, i) => (
            <motion.span
              key={i}
              className={i <= viz.currentStep ? "text-zinc-900 dark:text-zinc-100" : "text-zinc-300 dark:text-zinc-600"}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.02 }}
            >
              {token}
            </motion.span>
          ))}
          {viz.currentStep < STREAM_TOKENS.length - 1 && (
            <motion.span
              className="inline-block w-0.5 h-4 bg-blue-500 ml-0.5"
              animate={{ opacity: [1, 0] }}
              transition={{ repeat: Infinity, duration: 0.5 }}
            />
          )}
        </div>
      </div>
      <div className="text-xs text-[var(--color-text-secondary)]">
        Token {viz.currentStep + 1} of {STREAM_TOKENS.length}
      </div>
    </div>
  );
}
