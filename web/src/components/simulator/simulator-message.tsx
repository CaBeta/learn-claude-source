"use client";
import { motion } from "framer-motion";
import type { SimStep } from "@/types/agent-data";

interface SimulatorMessageProps {
  step: SimStep;
  isActive: boolean;
}

const TYPE_STYLES: Record<string, { bg: string; border: string; icon: string }> = {
  system: { bg: "bg-zinc-100 dark:bg-zinc-800", border: "border-zinc-300 dark:border-zinc-600", icon: "S" },
  user_input: { bg: "bg-blue-50 dark:bg-blue-900/20", border: "border-blue-300 dark:border-blue-700", icon: "U" },
  think: { bg: "bg-emerald-50 dark:bg-emerald-900/20", border: "border-emerald-300 dark:border-emerald-700", icon: "T" },
  tool_call: { bg: "bg-purple-50 dark:bg-purple-900/20", border: "border-purple-300 dark:border-purple-700", icon: "TC" },
  tool_result: { bg: "bg-amber-50 dark:bg-amber-900/20", border: "border-amber-300 dark:border-amber-700", icon: "TR" },
  response: { bg: "bg-sky-50 dark:bg-sky-900/20", border: "border-sky-300 dark:border-sky-700", icon: "R" },
  decision: { bg: "bg-rose-50 dark:bg-rose-900/20", border: "border-rose-300 dark:border-rose-700", icon: "D" },
  error: { bg: "bg-red-50 dark:bg-red-900/20", border: "border-red-300 dark:border-red-700", icon: "!" },
};

export function SimulatorMessage({ step, isActive }: SimulatorMessageProps) {
  const style = TYPE_STYLES[step.type] || TYPE_STYLES.system;

  return (
    <motion.div
      className={`rounded-lg border ${style.border} ${style.bg} p-3 transition-all ${
        isActive ? "ring-2 ring-blue-400 ring-offset-1" : ""
      }`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className={`inline-flex h-5 w-5 items-center justify-center rounded text-xs font-bold ${
            step.type === "tool_call"
              ? "bg-purple-500 text-white"
              : step.type === "think"
              ? "bg-emerald-500 text-white"
              : "bg-zinc-400 text-white"
          }`}
        >
          {style.icon}
        </span>
        <span className="text-xs font-semibold">{step.label}</span>
        {step.toolName && (
          <span className="rounded bg-purple-200 px-1.5 py-0.5 text-xs font-mono text-purple-700 dark:bg-purple-800 dark:text-purple-200">
            {step.toolName}
          </span>
        )}
      </div>
      <p className="text-sm text-[var(--color-text-secondary)]">{step.detail}</p>
      {step.toolInput && (
        <pre className="mt-2 rounded bg-zinc-100 p-2 text-xs dark:bg-zinc-800 overflow-x-auto">
          {JSON.stringify(step.toolInput, null, 2)}
        </pre>
      )}
      {step.toolOutput && (
        <pre className="mt-2 rounded bg-zinc-100 p-2 text-xs dark:bg-zinc-800 overflow-x-auto">
          {step.toolOutput}
        </pre>
      )}
    </motion.div>
  );
}
