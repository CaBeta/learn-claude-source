"use client";
import { motion } from "framer-motion";

interface WhatsNewProps {
  diff: {
    newClasses: string[];
    newFunctions: string[];
    newTools: string[];
    locDelta: number;
  };
}

export function WhatsNew({ diff }: WhatsNewProps) {
  const items = [
    { label: "Lines Added", value: diff.locDelta, color: "text-blue-500" },
    { label: "New Classes", value: diff.newClasses.length, color: "text-emerald-500" },
    { label: "New Functions", value: diff.newFunctions.length, color: "text-amber-500" },
    { label: "New Tools", value: diff.newTools.length, color: "text-purple-500" },
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">What&apos;s New</h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {items.map((item, i) => (
          <motion.div
            key={item.label}
            className="rounded-lg border border-[var(--color-border)] p-4 text-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <div className={`text-2xl font-bold ${item.color}`}>+{item.value}</div>
            <div className="text-xs text-[var(--color-text-secondary)] mt-1">
              {item.label}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Details */}
      {(diff.newClasses.length > 0 || diff.newFunctions.length > 0 || diff.newTools.length > 0) && (
        <div className="space-y-3">
          {diff.newClasses.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-1">New Classes</h4>
              <div className="flex flex-wrap gap-1">
                {diff.newClasses.map((cls) => (
                  <span key={cls} className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-mono text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                    {cls}
                  </span>
                ))}
              </div>
            </div>
          )}
          {diff.newFunctions.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-1">New Functions</h4>
              <div className="flex flex-wrap gap-1">
                {diff.newFunctions.slice(0, 15).map((fn) => (
                  <span key={fn} className="rounded bg-amber-100 px-2 py-0.5 text-xs font-mono text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                    {fn}
                  </span>
                ))}
                {diff.newFunctions.length > 15 && (
                  <span className="text-xs text-[var(--color-text-secondary)]">
                    +{diff.newFunctions.length - 15} more
                  </span>
                )}
              </div>
            </div>
          )}
          {diff.newTools.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-1">New Tools</h4>
              <div className="flex flex-wrap gap-1">
                {diff.newTools.map((tool) => (
                  <span key={tool} className="rounded bg-purple-100 px-2 py-0.5 text-xs font-mono text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                    {tool}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
