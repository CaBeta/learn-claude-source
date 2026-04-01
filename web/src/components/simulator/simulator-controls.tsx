"use client";

interface SimulatorControlsProps {
  isPlaying: boolean;
  canPlay: boolean;
  currentStep: number;
  totalSteps: number;
  onPlay: () => void;
  onPause: () => void;
  onReset: () => void;
  onNext: () => void;
  onPrev: () => void;
  onSpeedChange: (speed: number) => void;
}

const SPEED_OPTIONS = [
  { label: "0.5x", value: 2000 },
  { label: "1x", value: 1000 },
  { label: "2x", value: 500 },
  { label: "4x", value: 250 },
];

export function SimulatorControls({
  isPlaying,
  canPlay,
  currentStep,
  totalSteps,
  onPlay,
  onPause,
  onReset,
  onNext,
  onPrev,
  onSpeedChange,
}: SimulatorControlsProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-3">
      <button
        onClick={onReset}
        className="rounded-md px-2 py-1 text-xs text-[var(--color-text-secondary)] hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
        title="Reset"
      >
        Reset
      </button>
      <button
        onClick={onPrev}
        disabled={currentStep === 0}
        className="rounded-md px-2 py-1 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 transition-colors"
      >
        Prev
      </button>
      {isPlaying ? (
        <button
          onClick={onPause}
          className="rounded-md bg-amber-500 px-4 py-1 text-sm font-medium text-white hover:bg-amber-600 transition-colors"
        >
          Pause
        </button>
      ) : (
        <button
          onClick={onPlay}
          disabled={!canPlay}
          className="rounded-md bg-emerald-500 px-4 py-1 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-30 transition-colors"
        >
          Play
        </button>
      )}
      <button
        onClick={onNext}
        disabled={currentStep >= totalSteps - 1}
        className="rounded-md px-2 py-1 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 transition-colors"
      >
        Next
      </button>
      <div className="ml-auto flex items-center gap-1">
        {SPEED_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onSpeedChange(opt.value)}
            className="rounded px-1.5 py-0.5 text-xs text-[var(--color-text-secondary)] hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            {opt.label}
          </button>
        ))}
      </div>
      <div className="text-xs text-[var(--color-text-secondary)] tabular-nums">
        {currentStep + 1}/{totalSteps}
      </div>
    </div>
  );
}
