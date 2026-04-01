"use client";
import { Timeline } from "@/components/timeline/timeline";

export default function TimelinePage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Timeline</h1>
        <p className="mt-2 text-[var(--color-text-secondary)]">
          12 sessions from basic agent loop to production agent
        </p>
      </div>
      <Timeline />
    </div>
  );
}
