"use client";
import { VERSION_META, LAYERS } from "@/lib/constants";
import { LayerBadge } from "@/components/ui/badge";

interface ArchDiagramProps {
  version: string;
}

const LAYER_COLORS: Record<string, string> = {
  core: "border-blue-500 bg-blue-500/10",
  intelligence: "border-emerald-500 bg-emerald-500/10",
  extension: "border-amber-500 bg-amber-500/10",
  production: "border-red-500 bg-red-500/10",
};

const LAYER_TEXT_COLORS: Record<string, string> = {
  core: "text-blue-600 dark:text-blue-400",
  intelligence: "text-emerald-600 dark:text-emerald-400",
  extension: "text-amber-600 dark:text-amber-400",
  production: "text-red-600 dark:text-red-400",
};

export function ArchDiagram({ version }: ArchDiagramProps) {
  const meta = VERSION_META[version];
  if (!meta) return null;

  const currentLayer = LAYERS.find((l) => l.id === meta.layer);

  // Find all layers up to and including the current version's layer
  const relevantLayers = currentLayer
    ? LAYERS.slice(0, LAYERS.indexOf(currentLayer) + 1)
    : LAYERS;

  return (
    <div className="space-y-3">
      <div className="text-sm font-medium text-[var(--color-text-secondary)]">
        Architecture through {version}
      </div>
      <div className="space-y-2">
        {relevantLayers.map((layer) => {
          const isActiveLayer = layer.id === meta.layer;
          return (
            <div
              key={layer.id}
              className={`rounded-lg border-2 p-3 transition-all ${
                isActiveLayer
                  ? LAYER_COLORS[layer.id]
                  : "border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800/50"
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <LayerBadge layer={layer.id}>{layer.label}</LayerBadge>
                {isActiveLayer && (
                  <span className={`text-xs ${LAYER_TEXT_COLORS[layer.id]}`}>
                    (current)
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-1">
                {layer.versions.map((vid) => {
                  const vMeta = VERSION_META[vid];
                  const isCurrent = vid === version;
                  const isPast =
                    layer.versions.indexOf(vid) <
                      layer.versions.indexOf(version) ||
                    LAYERS.indexOf(layer) < LAYERS.indexOf(currentLayer!);
                  return (
                    <span
                      key={vid}
                      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-mono ${
                        isCurrent
                          ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                          : isPast
                          ? "bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300"
                          : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500"
                      }`}
                    >
                      {vid}: {vMeta?.title}
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
