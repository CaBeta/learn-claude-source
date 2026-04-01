"use client";
import { useState, useEffect, useCallback } from "react";

interface SteppedVisualizationState {
  currentStep: number;
  totalSteps: number;
  isPlaying: boolean;
  speed: number;
}

export function useSteppedVisualization(totalSteps: number) {
  const [state, setState] = useState<SteppedVisualizationState>({
    currentStep: 0,
    totalSteps,
    isPlaying: false,
    speed: 1000,
  });

  useEffect(() => {
    if (!state.isPlaying) return;

    const timer = setInterval(() => {
      setState((prev) => {
        if (prev.currentStep >= prev.totalSteps - 1) {
          return { ...prev, isPlaying: false };
        }
        return { ...prev, currentStep: prev.currentStep + 1 };
      });
    }, state.speed);

    return () => clearInterval(timer);
  }, [state.isPlaying, state.speed, state.totalSteps]);

  const goTo = useCallback((step: number) => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.max(0, Math.min(step, prev.totalSteps - 1)),
    }));
  }, [state.totalSteps]);

  const next = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.min(prev.currentStep + 1, prev.totalSteps - 1),
    }));
  }, [state.totalSteps]);

  const prev = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.max(prev.currentStep - 1, 0),
    }));
  }, []);

  const play = useCallback(() => {
    setState((prev) => {
      if (prev.currentStep >= prev.totalSteps - 1) {
        return { ...prev, currentStep: 0, isPlaying: true };
      }
      return { ...prev, isPlaying: true };
    });
  }, [state.totalSteps]);

  const pause = useCallback(() => {
    setState((prev) => ({ ...prev, isPlaying: false }));
  }, []);

  const reset = useCallback(() => {
    setState((prev) => ({ ...prev, currentStep: 0, isPlaying: false }));
  }, []);

  const setSpeed = useCallback((speed: number) => {
    setState((prev) => ({ ...prev, speed }));
  }, []);

  return {
    currentStep: state.currentStep,
    isPlaying: state.isPlaying,
    speed: state.speed,
    goTo,
    next,
    prev,
    play,
    pause,
    reset,
    setSpeed,
    isAtEnd: state.currentStep >= state.totalSteps - 1,
    isAtStart: state.currentStep === 0,
  };
}
