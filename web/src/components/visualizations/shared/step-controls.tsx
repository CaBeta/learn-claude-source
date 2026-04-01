"use client";

interface StepControlsProps {
  currentStep: number;
  totalSteps: number;
  isPlaying: boolean;
  onPlay: () => void;
  onPause: () => void;
  onNext: () => void;
  onPrev: () => void;
  onReset: () => void;
}

export function StepControls({
  currentStep,
  totalSteps,
  isPlaying,
  onPlay,
  onPause,
  onNext,
  onPrev,
  onReset,
}: StepControlsProps) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onReset}
        className="rounded px-2 py-1 text-xs text-[var(--color-text-secondary)] hover:bg-zinc-100 dark:hover:bg-zinc-800"
      >
        Reset
      </button>
      <button
        onClick={onPrev}
        disabled={currentStep === 0}
        className="rounded px-2 py-1 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30"
      >
        Prev
      </button>
      {isPlaying ? (
        <button
          onClick={onPause}
          className="rounded bg-amber-500 px-3 py-1 text-xs font-medium text-white"
        >
          Pause
        </button>
      ) : (
        <button
          onClick={onPlay}
          className="rounded bg-emerald-500 px-3 py-1 text-xs font-medium text-white"
        >
          Play
        </button>
      )}
      <button
        onClick={onNext}
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
