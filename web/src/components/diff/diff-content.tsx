"use client";

interface DiffContentProps {
  oldSource: string;
  newSource: string;
}

export function DiffContent({ oldSource, newSource }: DiffContentProps) {
  const oldLines = oldSource.split("\n");
  const newLines = newSource.split("\n");
  const maxLines = Math.max(oldLines.length, newLines.length);

  return (
    <div className="grid grid-cols-2 gap-0 overflow-hidden rounded-lg border border-[var(--color-border)]">
      <div className="border-r border-[var(--color-border)]">
        <div className="border-b border-[var(--color-border)] bg-zinc-100 px-3 py-1 text-xs font-medium dark:bg-zinc-800">
          Before
        </div>
        <pre className="overflow-auto bg-zinc-950 p-3 text-xs text-zinc-300 max-h-[400px]">
          {oldLines.map((line, i) => (
            <div key={i}>
              <span className="mr-3 inline-block w-8 text-right text-zinc-600">{i + 1}</span>
              {line}
            </div>
          ))}
        </pre>
      </div>
      <div>
        <div className="border-b border-[var(--color-border)] bg-zinc-100 px-3 py-1 text-xs font-medium dark:bg-zinc-800">
          After
        </div>
        <pre className="overflow-auto bg-zinc-950 p-3 text-xs text-zinc-300 max-h-[400px]">
          {newLines.map((line, i) => (
            <div key={i}>
              <span className="mr-3 inline-block w-8 text-right text-zinc-600">{i + 1}</span>
              {line}
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
}
