"use client";
import { useState, useCallback } from "react";
import type { SimStep } from "@/types/agent-data";

interface SimulatorState {
  currentStep: number;
  isRunning: boolean;
  speed: number;
}

export function useSimulator(steps: SimStep[]) {
  const [state, setState] = useState<SimulatorState>({
    currentStep: 0,
    isRunning: false,
    speed: 1,
  });

  const play = useCallback(() => {
    setState((prev) => ({ ...prev, isRunning: true }));
  }, []);

  const pause = useCallback(() => {
    setState((prev) => ({ ...prev, isRunning: false }));
  }, []);

  const reset = useCallback(() => {
    setState({ currentStep: 0, isRunning: false, speed: 1 });
  }, []);

  const next = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.min(prev.currentStep + 1, steps.length - 1),
    }));
  }, [steps.length]);

  const prev = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.max(prev.currentStep - 1, 0),
    }));
  }, []);

  const setSpeed = useCallback((speed: number) => {
    setState((prev) => ({ ...prev, speed }));
  }, []);

  const setStep = useCallback((step: number) => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.max(0, Math.min(step, steps.length - 1)),
    }));
  }, [steps.length]);

  return {
    ...state,
    steps,
    currentStepData: steps[state.currentStep] ?? null,
    play,
    pause,
    reset,
    next,
    prev,
    setSpeed,
    setStep,
    isAtEnd: state.currentStep >= steps.length - 1,
    isAtStart: state.currentStep === 0,
  };
}
