"use client";

import { DocRenderer } from "@/components/docs/doc-renderer";
import { SourceViewer } from "@/components/code/source-viewer";
import { Tabs } from "@/components/ui/tabs";

interface VersionDetailClientProps {
  version: string;
  diff: {
    from: string;
    to: string;
    newClasses: string[];
    newFunctions: string[];
    newTools: string[];
    locDelta: number;
  } | null;
  source: string;
  filename: string;
}

export function VersionDetailClient({
  version,
  diff,
  source,
  filename,
}: VersionDetailClientProps) {
  const tabs = [
    { id: "learn", label: "学习" },
    { id: "code", label: "代码" },
    { id: "deep-dive", label: "深入" },
  ];

  return (
    <div className="space-y-6">
      <Tabs tabs={tabs} defaultTab="learn">
        {(activeTab) => (
          <>
            {activeTab === "learn" && <DocRenderer version={version} />}
            {activeTab === "code" && (
              <SourceViewer source={source} filename={filename} />
            )}
            {activeTab === "deep-dive" && (
              <div className="space-y-8">
                {/* What's New */}
                {diff && (
                  <section>
                    <h2 className="mb-4 text-xl font-semibold">变化概览</h2>
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                      <div className="rounded-lg border border-[var(--color-border)] p-3 text-center">
                        <div className="text-2xl font-bold text-blue-500">
                          +{diff.locDelta}
                        </div>
                        <div className="text-xs text-[var(--color-text-secondary)]">代码行数</div>
                      </div>
                      <div className="rounded-lg border border-[var(--color-border)] p-3 text-center">
                        <div className="text-2xl font-bold text-emerald-500">
                          {diff.newClasses.length}
                        </div>
                        <div className="text-xs text-[var(--color-text-secondary)]">新增类</div>
                      </div>
                      <div className="rounded-lg border border-[var(--color-border)] p-3 text-center">
                        <div className="text-2xl font-bold text-amber-500">
                          {diff.newFunctions.length}
                        </div>
                        <div className="text-xs text-[var(--color-text-secondary)]">新增函数</div>
                      </div>
                      <div className="rounded-lg border border-[var(--color-border)] p-3 text-center">
                        <div className="text-2xl font-bold text-red-500">
                          {diff.newTools.length}
                        </div>
                        <div className="text-xs text-[var(--color-text-secondary)]">新增工具</div>
                      </div>
                    </div>
                    {(diff.newClasses.length > 0 || diff.newFunctions.length > 0) && (
                      <div className="mt-4 space-y-2">
                        {diff.newClasses.length > 0 && (
                          <div>
                            <span className="text-sm font-medium">新增类: </span>
                            <span className="text-sm text-[var(--color-text-secondary)]">
                              {diff.newClasses.join(", ")}
                            </span>
                          </div>
                        )}
                        {diff.newFunctions.length > 0 && (
                          <div>
                            <span className="text-sm font-medium">新增函数: </span>
                            <span className="text-sm text-[var(--color-text-secondary)]">
                              {diff.newFunctions.slice(0, 10).join(", ")}
                              {diff.newFunctions.length > 10 ? "..." : ""}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </section>
                )}

                {/* Architecture reference */}
                <section>
                  <h2 className="mb-4 text-xl font-semibold">Claude Code 源码对照</h2>
                  <div className="rounded-lg border border-[var(--color-border)] bg-zinc-50 p-4 dark:bg-zinc-800/50">
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      本节实现的机制对应 Claude Code 源码中的核心模式。
                      详细对照请查看课程文档中的「Claude Code 源码对照」部分。
                    </p>
                  </div>
                </section>
              </div>
            )}
          </>
        )}
      </Tabs>
    </div>
  );
}
