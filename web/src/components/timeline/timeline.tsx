"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { LEARNING_PATH, VERSION_META, LAYERS } from "@/lib/constants";
import { LayerBadge } from "@/components/ui/badge";

const LAYER_COLORS: Record<string, string> = {
  core: "bg-blue-500",
  intelligence: "bg-emerald-500",
  extension: "bg-amber-500",
  production: "bg-red-500",
};

export function Timeline() {
  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-zinc-200 dark:bg-zinc-700" />

      <div className="space-y-6">
        {LEARNING_PATH.map((versionId, index) => {
          const meta = VERSION_META[versionId];
          if (!meta) return null;
          const layer = LAYERS.find((l) => l.id === meta.layer);

          return (
            <motion.div
              key={versionId}
              className="relative pl-16"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05, duration: 0.3 }}
            >
              {/* Timeline dot */}
              <div
                className={`absolute left-4 top-3 h-4 w-4 rounded-full border-2 border-white dark:border-zinc-900 ${
                  LAYER_COLORS[meta.layer]
                }`}
              />

              <Link
                href={`/learn/${versionId}`}
                className="block rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4 transition-all hover:border-zinc-400 hover:shadow-sm dark:hover:border-zinc-500"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-mono text-lg font-bold">{versionId}</span>
                  <LayerBadge layer={meta.layer}>
                    {layer?.label}
                  </LayerBadge>
                  <span className="ml-auto text-xs text-[var(--color-text-secondary)]">
                    Session {index + 1}/12
                  </span>
                </div>
                <h3 className="text-base font-semibold">{meta.title}</h3>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                  {meta.subtitle}
                </p>
                {meta.keyInsight && (
                  <p className="mt-2 text-xs italic text-[var(--color-text-secondary)]">
                    {meta.keyInsight}
                  </p>
                )}
              </Link>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
