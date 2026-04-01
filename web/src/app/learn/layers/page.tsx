"use client";
import Link from "next/link";
import { LAYERS, VERSION_META } from "@/lib/constants";
import { LayerBadge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import versionsData from "@/data/generated/versions.json";

const LAYER_BORDER_CLASSES: Record<string, string> = {
  core: "border-l-blue-500",
  intelligence: "border-l-emerald-500",
  extension: "border-l-amber-500",
  production: "border-l-red-500",
};

const LAYER_HEADER_BG: Record<string, string> = {
  core: "bg-blue-500",
  intelligence: "bg-emerald-500",
  extension: "bg-amber-500",
  production: "bg-red-500",
};

export default function LayersPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Layers Overview</h1>
        <p className="mt-2 text-[var(--color-text-secondary)]">
          Four architectural layers, from core loop to production agent
        </p>
      </div>

      <div className="space-y-6">
        {LAYERS.map((layer, layerIdx) => (
          <div key={layer.id}>
            <div
              className={`rounded-lg border-l-4 ${LAYER_BORDER_CLASSES[layer.id]} border border-[var(--color-border)] overflow-hidden`}
            >
              <div className="flex items-center gap-3 border-b border-[var(--color-border)] p-4">
                <div className={`h-3 w-3 rounded-full ${LAYER_HEADER_BG[layer.id]}`} />
                <span className="text-lg font-semibold">
                  L{layerIdx + 1}: {layer.label}
                </span>
                <span className="text-sm text-[var(--color-text-secondary)]">
                  {layer.versions.length} sessions
                </span>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {layer.versions.map((vid) => {
                    const meta = VERSION_META[vid];
                    const data = (versionsData as any).versions?.find((v: any) => v.id === vid);
                    if (!meta) return null;
                    return (
                      <Link key={vid} href={`/learn/${vid}`} className="block">
                        <Card className="h-full transition-all hover:shadow-md hover:border-zinc-400 dark:hover:border-zinc-500">
                          <div className="flex items-center gap-2 mb-2">
                            <LayerBadge layer={layer.id}>{vid}</LayerBadge>
                          </div>
                          <h3 className="font-semibold">{meta.title}</h3>
                          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                            {meta.subtitle}
                          </p>
                          {data && (
                            <div className="mt-2 text-xs text-[var(--color-text-secondary)]">
                              {data.loc} LOC | {(data.tools || []).length} tools
                            </div>
                          )}
                          {meta.keyInsight && (
                            <p className="mt-2 text-xs italic text-[var(--color-text-secondary)]">
                              {meta.keyInsight}
                            </p>
                          )}
                        </Card>
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Arrow between layers */}
            {layerIdx < LAYERS.length - 1 && (
              <div className="flex justify-center py-2">
                <svg className="h-6 w-6 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
