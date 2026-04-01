"use client";
import { useState, useEffect, useCallback } from "react";
import { SimulatorControls } from "./simulator-controls";
import { SimulatorMessage } from "./simulator-message";
import type { SimStep } from "@/types/agent-data";

interface AgentLoopSimulatorProps {
  version: string;
}

// Default simulation steps for each version
const DEFAULT_STEPS: Record<string, SimStep[]> = {
  s01: [
    { type: "system", label: "System", detail: "Agent initialized with while(true) loop" },
    { type: "user_input", label: "User", detail: "Help me refactor the authentication module" },
    { type: "think", label: "Think", detail: "Analyzing the request. Need to understand the current auth module structure." },
    { type: "tool_call", label: "Tool Call", detail: "Reading the auth module files", toolName: "read_file", toolInput: { path: "auth.py" } },
    { type: "tool_result", label: "Tool Result", detail: "File contents: class Authenticator: ..." },
    { type: "think", label: "Think", detail: "I can see the auth module uses a monolithic class. I'll refactor it into separate concerns." },
    { type: "response", label: "Response", detail: "I'll refactor the authentication module into separate classes for token management, session handling, and user validation." },
  ],
  s02: [
    { type: "system", label: "System", detail: "Agent initialized with tool dispatch map" },
    { type: "user_input", label: "User", detail: "Find all TODO comments in the codebase" },
    { type: "think", label: "Think", detail: "I need to search through the codebase files for TODO comments." },
    { type: "tool_call", label: "Tool Call", detail: "Searching for TODO patterns", toolName: "search_files", toolInput: { pattern: "TODO", path: "." } },
    { type: "tool_result", label: "Tool Result", detail: "Found 15 TODO comments across 8 files" },
    { type: "response", label: "Response", detail: "I found 15 TODO comments. Let me list them organized by file." },
  ],
  s03: [
    { type: "system", label: "System", detail: "Agent initialized with streaming support" },
    { type: "user_input", label: "User", detail: "Explain the architecture" },
    { type: "think", label: "Think", detail: "Streaming token by token..." },
    { type: "response", label: "Response (streamed)", detail: "The architecture follows a layered approach..." },
  ],
  s04: [
    { type: "system", label: "System", detail: "Agent initialized with subagent support" },
    { type: "user_input", label: "User", detail: "Refactor the entire backend and update tests" },
    { type: "think", label: "Think", detail: "This is a large task. I'll spawn subagents for different parts." },
    { type: "tool_call", label: "Spawn SubAgent", detail: "Creating subagent for backend refactoring", toolName: "spawn_subagent", toolInput: { task: "refactor backend" } },
    { type: "tool_result", label: "SubAgent Result", detail: "Backend refactored: 3 files modified" },
    { type: "tool_call", label: "Spawn SubAgent", detail: "Creating subagent for test updates", toolName: "spawn_subagent", toolInput: { task: "update tests" } },
    { type: "tool_result", label: "SubAgent Result", detail: "Tests updated: 12 tests passing" },
    { type: "response", label: "Response", detail: "Both subtasks completed successfully." },
  ],
  s05: [
    { type: "system", label: "System", detail: "Agent initialized with context management" },
    { type: "user_input", label: "User", detail: "Continue working on the large project" },
    { type: "think", label: "Context Compression", detail: "Context window approaching limit. Applying 5-layer compression pipeline..." },
    { type: "system", label: "Context Manager", detail: "Applied: sliding window (removed 50 old messages), summarization, tool result truncation" },
    { type: "think", label: "Think", detail: "Context compressed. Now I can continue with the task." },
    { type: "response", label: "Response", detail: "I've managed the context and can continue working." },
  ],
};

function getStepsForVersion(version: string): SimStep[] {
  return DEFAULT_STEPS[version] || DEFAULT_STEPS.s01;
}

export function AgentLoopSimulator({ version }: AgentLoopSimulatorProps) {
  const steps = getStepsForVersion(version);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1000);

  useEffect(() => {
    if (!isPlaying || currentStep >= steps.length - 1) {
      if (currentStep >= steps.length - 1) setIsPlaying(false);
      return;
    }
    const timer = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= steps.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, speed);
    return () => clearInterval(timer);
  }, [isPlaying, speed, steps.length, currentStep]);

  const play = useCallback(() => {
    if (currentStep >= steps.length - 1) setCurrentStep(0);
    setIsPlaying(true);
  }, [currentStep, steps.length]);

  const pause = useCallback(() => setIsPlaying(false), []);
  const reset = useCallback(() => {
    setCurrentStep(0);
    setIsPlaying(false);
  }, []);

  const visibleSteps = steps.slice(0, currentStep + 1);

  return (
    <div className="space-y-4">
      <SimulatorControls
        isPlaying={isPlaying}
        canPlay={true}
        currentStep={currentStep}
        totalSteps={steps.length}
        onPlay={play}
        onPause={pause}
        onReset={reset}
        onNext={() => setCurrentStep((p) => Math.min(p + 1, steps.length - 1))}
        onPrev={() => setCurrentStep((p) => Math.max(p - 1, 0))}
        onSpeedChange={setSpeed}
      />
      <div className="space-y-2 max-h-[500px] overflow-y-auto rounded-lg border border-[var(--color-border)] p-4 bg-zinc-50 dark:bg-zinc-800/50">
        {visibleSteps.map((step, i) => (
          <SimulatorMessage key={i} step={step} isActive={i === currentStep} />
        ))}
        {currentStep < steps.length - 1 && (
          <div className="text-center text-xs text-[var(--color-text-secondary)] py-2">
            {steps.length - currentStep - 1} more steps...
          </div>
        )}
      </div>
    </div>
  );
}
