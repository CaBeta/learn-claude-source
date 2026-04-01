"use client";
import { useState, useMemo } from "react";
import { VERSION_ORDER, VERSION_META, LAYERS } from "@/lib/constants";
import { LayerBadge } from "@/components/ui/badge";
import { CodeDiff } from "@/components/diff/code-diff";
import versionsData from "@/data/generated/versions.json";

export default function ComparePage() {
  const [versionA, setVersionA] = useState("s01");
  const [versionB, setVersionB] = useState("s02");

  const dataA = useMemo(
    () => (versionsData as any).versions?.find((v: any) => v.id === versionA),
    [versionA]
  );
  const dataB = useMemo(
    () => (versionsData as any).versions?.find((v: any) => v.id === versionB),
    [versionB]
  );
  const metaA = VERSION_META[versionA];
  const metaB = VERSION_META[versionB];

  const comparison = useMemo(() => {
    if (!dataA || !dataB) return null;
    const toolsA: string[] = dataA.tools || [];
    const toolsB: string[] = dataB.tools || [];
    return {
      locDelta: dataB.loc - dataA.loc,
      toolsOnlyA: toolsA.filter((t: string) => !toolsB.includes(t)),
      toolsOnlyB: toolsB.filter((t: string) => !toolsA.includes(t)),
      toolsShared: toolsA.filter((t: string) => toolsB.includes(t)),
      newClasses: (dataB.classes || []).filter((c: string) => !(dataA.classes || []).includes(c)),
      newFunctions: (dataB.functions || []).filter((f: string) => !(dataA.functions || []).includes(f)),
    };
  }, [dataA, dataB]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Version Comparison</h1>
        <p className="mt-2 text-[var(--color-text-secondary)]">
          Compare two versions side by side
        </p>
      </div>

      {/* Selectors */}
      <div className="flex items-center gap-4">
        <select
          value={versionA}
          onChange={(e) => setVersionA(e.target.value)}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-sm"
        >
          {VERSION_ORDER.map((v) => (
            <option key={v} value={v}>{v}: {VERSION_META[v]?.title}</option>
          ))}
        </select>
        <span className="text-[var(--color-text-secondary)]">vs</span>
        <select
          value={versionB}
          onChange={(e) => setVersionB(e.target.value)}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-sm"
        >
          {VERSION_ORDER.map((v) => (
            <option key={v} value={v}>{v}: {VERSION_META[v]?.title}</option>
          ))}
        </select>
      </div>

      {/* Version Info Cards */}
      {dataA && dataB && (
        <div className="grid grid-cols-2 gap-4">
          {[{ data: dataA, meta: metaA, v: versionA }, { data: dataB, meta: metaB, v: versionB }].map(
            ({ data, meta, v }) => (
              <div key={v} className="rounded-lg border border-[var(--color-border)] p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono font-bold">{v}</span>
                  {meta && <LayerBadge layer={meta.layer}>{meta.title}</LayerBadge>}
                </div>
                <div className="text-sm text-[var(--color-text-secondary)]">
                  {data.loc} LOC | {(data.tools || []).length} tools
                </div>
              </div>
            )
          )}
        </div>
      )}

      {/* Structural Diff */}
      {comparison && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Structural Changes</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg border border-[var(--color-border)] p-3 text-center">
              <div className={`text-2xl font-bold ${comparison.locDelta >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                {comparison.locDelta >= 0 ? "+" : ""}{comparison.locDelta}
              </div>
              <div className="text-xs text-[var(--color-text-secondary)]">LOC Delta</div>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] p-3 text-center">
              <div className="text-2xl font-bold text-emerald-500">{comparison.toolsOnlyB.length}</div>
              <div className="text-xs text-[var(--color-text-secondary)]">New Tools</div>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] p-3 text-center">
              <div className="text-2xl font-bold text-amber-500">{comparison.newClasses.length}</div>
              <div className="text-xs text-[var(--color-text-secondary)]">New Classes</div>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] p-3 text-center">
              <div className="text-2xl font-bold text-purple-500">{comparison.newFunctions.length}</div>
              <div className="text-xs text-[var(--color-text-secondary)]">New Functions</div>
            </div>
          </div>

          {/* Tool Comparison */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Tool Comparison</h3>
            <div className="flex flex-wrap gap-1">
              {comparison.toolsOnlyA.map((t) => (
                <span key={t} className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
                  {t} (A only)
                </span>
              ))}
              {comparison.toolsShared.map((t) => (
                <span key={t} className="rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                  {t}
                </span>
              ))}
              {comparison.toolsOnlyB.map((t) => (
                <span key={t} className="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                  {t} (B only)
                </span>
              ))}
            </div>
          </div>

          {/* Code Diff */}
          {dataA.source && dataB.source && (
            <CodeDiff
              oldSource={dataA.source}
              newSource={dataB.source}
              oldFilename={dataA.filename}
              newFilename={dataB.filename}
            />
          )}
        </div>
      )}
    </div>
  );
}
