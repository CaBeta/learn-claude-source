"use client";

interface StepControlsProps {
  currentStep: number;
  totalSteps: number;
  isPlaying: boolean;
  play: () => void;
  pause: () => void;
  next: () => void;
  prev: () => void;
  reset: () => void;
}

export function StepControls({
  currentStep,
  totalSteps,
  isPlaying,
  play,
  pause,
  next,
  prev,
  reset,
}: StepControlsProps) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={reset}
        className="rounded px-2 py-1 text-xs text-[var(--color-text-secondary)] hover:bg-zinc-100 dark:hover:bg-zinc-800"
      >
        Reset
      </button>
      <button
        onClick={prev}
        disabled={currentStep === 0}
        className="rounded px-2 py-1 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30"
      >
        Prev
      </button>
      {isPlaying ? (
        <button
          onClick={pause}
          className="rounded bg-amber-500 px-3 py-1 text-xs font-medium text-white"
        >
          Pause
        </button>
      ) : (
        <button
          onClick={play}
          className="rounded bg-emerald-500 px-3 py-1 text-xs font-medium text-white"
        >
          Play
        </button>
      )}
      <button
        onClick={next}
        disabled={currentStep >= totalSteps - 1}
        className="rounded px-2 py-1 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30"
      >
        Next
      </button>
      <div className="ml-2 text-xs tabular-nums text-[var(--color-text-secondary)]">
        {currentStep + 1}/{totalSteps}
      </div>
    </div>
  );
}
