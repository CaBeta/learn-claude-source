"use client";
import { useMemo } from "react";

interface CodeDiffProps {
  oldSource: string;
  newSource: string;
  oldFilename?: string;
  newFilename?: string;
}

interface DiffLine {
  type: "add" | "remove" | "context";
  content: string;
  oldLine?: number;
  newLine?: number;
}

function computeDiff(oldLines: string[], newLines: string[]): DiffLine[] {
  // Simple LCS-based diff
  const result: DiffLine[] = [];
  const maxLen = Math.max(oldLines.length, newLines.length);

  // Simple approach: show all old lines as removed, all new lines as added
  // with context matching where lines are identical
  let oi = 0;
  let ni = 0;

  while (oi < oldLines.length || ni < newLines.length) {
    if (oi < oldLines.length && ni < newLines.length && oldLines[oi] === newLines[ni]) {
      result.push({ type: "context", content: oldLines[oi], oldLine: oi + 1, newLine: ni + 1 });
      oi++;
      ni++;
    } else if (ni < newLines.length && (oi >= oldLines.length || oldLines[oi] !== newLines[ni])) {
      // Check if this line was added
      const foundInOld = oldLines.slice(oi).indexOf(newLines[ni]);
      if (foundInOld > 0 && foundInOld <= 3) {
        // Lines were removed
        for (let k = 0; k < foundInOld; k++) {
          result.push({ type: "remove", content: oldLines[oi + k], oldLine: oi + k + 1 });
        }
        oi += foundInOld;
      } else {
        result.push({ type: "add", content: newLines[ni], newLine: ni + 1 });
        ni++;
      }
    } else if (oi < oldLines.length) {
      result.push({ type: "remove", content: oldLines[oi], oldLine: oi + 1 });
      oi++;
    } else {
      result.push({ type: "add", content: newLines[ni], newLine: ni + 1 });
      ni++;
    }
  }

  return result;
}

export function CodeDiff({ oldSource, newSource, oldFilename, newFilename }: CodeDiffProps) {
  const diffLines = useMemo(() => {
    const oldLines = (oldSource || "").split("\n");
    const newLines = (newSource || "").split("\n");
    return computeDiff(oldLines, newLines);
  }, [oldSource, newSource]);

  const addedCount = diffLines.filter((l) => l.type === "add").length;
  const removedCount = diffLines.filter((l) => l.type === "remove").length;

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--color-border)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-zinc-50 px-4 py-2 dark:bg-zinc-800/50">
        <div className="flex items-center gap-4">
          <span className="text-xs text-emerald-600 font-medium">
            +{addedCount}
          </span>
          <span className="text-xs text-red-600 font-medium">
            -{removedCount}
          </span>
        </div>
        <div className="text-xs text-[var(--color-text-secondary)]">
          {oldFilename || "before"} {"->"} {newFilename || "after"}
        </div>
      </div>

      {/* Diff Content */}
      <div className="max-h-[500px] overflow-auto bg-zinc-950 p-0">
        <table className="w-full text-sm font-mono">
          <tbody>
            {diffLines.map((line, i) => (
              <tr
                key={i}
                className={
                  line.type === "add"
                    ? "bg-emerald-950/40"
                    : line.type === "remove"
                    ? "bg-red-950/40"
                    : ""
                }
              >
                <td className="w-10 select-none px-2 text-right text-xs text-zinc-500">
                  {line.oldLine ?? ""}
                </td>
                <td className="w-10 select-none px-2 text-right text-xs text-zinc-500">
                  {line.newLine ?? ""}
                </td>
                <td className="w-5 select-none text-center text-xs">
                  {line.type === "add" ? (
                    <span className="text-emerald-500">+</span>
                  ) : line.type === "remove" ? (
                    <span className="text-red-500">-</span>
                  ) : (
                    <span className="text-zinc-600"> </span>
                  )}
                </td>
                <td className="whitespace-pre-wrap px-2 text-zinc-300">
                  {line.content}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
