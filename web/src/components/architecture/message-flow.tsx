"use client";
import { motion } from "framer-motion";

interface MessageFlowProps {
  version?: string;
}

const MESSAGE_TYPES = [
  { role: "user", label: "User Message", color: "bg-blue-500" },
  { role: "assistant", label: "Assistant Response", color: "bg-emerald-500" },
  { role: "tool_call", label: "Tool Call", color: "bg-purple-500" },
  { role: "tool_result", label: "Tool Result", color: "bg-amber-500" },
];

export function MessageFlow({ version }: MessageFlowProps) {
  return (
    <div className="space-y-4">
      <div className="text-sm font-medium text-[var(--color-text-secondary)]">
        Message Flow
      </div>
      <div className="space-y-2">
        {MESSAGE_TYPES.map((msg, i) => (
          <motion.div
            key={msg.role}
            className={`flex items-center gap-3 rounded-lg border border-[var(--color-border)] p-3`}
            initial={{ opacity: 0, x: i % 2 === 0 ? -20 : 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <div className={`h-3 w-3 rounded-full ${msg.color}`} />
            <div>
              <div className="text-sm font-medium">{msg.label}</div>
              <div className="text-xs text-[var(--color-text-secondary)]">
                {msg.role}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
      <div className="text-xs text-[var(--color-text-secondary)]">
        Messages flow between User, Agent, and Tools in a structured cycle.
      </div>
    </div>
  );
}
