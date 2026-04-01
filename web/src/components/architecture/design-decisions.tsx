"use client";
import { VERSION_META } from "@/lib/constants";

interface DesignDecisionsProps {
  version: string;
}

const DESIGN_DECISIONS: Record<string, Array<{ title: string; rationale: string }>> = {
  s01: [
    { title: "While-True Loop", rationale: "The agent loop is intentionally simple: call the model, check if it wants to use tools, execute tools, and repeat. This mirrors Claude Code's core execution model." },
    { title: "Message Accumulation", rationale: "All messages are appended to a single list, maintaining full conversation history for context continuity." },
  ],
  s02: [
    { title: "Dispatch Map Pattern", rationale: "Tools are registered in a dictionary mapping tool names to handler functions. This allows dynamic tool registration and clean separation of concerns." },
    { title: "Tool Schema Validation", rationale: "Each tool declares its input schema, enabling pre-execution validation before the handler runs." },
  ],
  s03: [
    { title: "Token-by-Token Streaming", rationale: "Streaming responses token by token reduces perceived latency. Users see output as it is generated rather than waiting for the complete response." },
    { title: "Stream Event Pipeline", rationale: "Stream events are processed through a pipeline that handles content, tool calls, and stop reasons incrementally." },
  ],
  s04: [
    { title: "SubAgent Isolation", rationale: "Each subagent receives its own message history, preventing cross-contamination of context between parent and child agents." },
    { title: "Hierarchical Delegation", rationale: "The parent agent delegates specific tasks to subagents, collecting their results to inform the overall task." },
  ],
  s05: [
    { title: "5-Layer Context Pipeline", rationale: "Context management uses 5 progressive compression layers: sliding window, summarization, tool result truncation, message deduplication, and relevance filtering." },
    { title: "Budget-Based Allocation", rationale: "Context budget is allocated proportionally, ensuring the most relevant information stays within the model's context window." },
  ],
  s06: [
    { title: "6 Permission Modes", rationale: "Permission checks range from auto-approve to always-ask, with graduated trust levels based on tool type and operation scope." },
    { title: "Pre/Post Hook Architecture", rationale: "Permission checks are implemented as pre-execution hooks that can allow, deny, or prompt the user." },
  ],
  s07: [
    { title: "Skill Loading Pipeline", rationale: "Skills are loaded lazily and cached, reducing initial startup time while keeping frequently used skills available." },
    { title: "Template-Based Definitions", rationale: "Skills use a template system with parameter substitution, allowing reusable patterns across different contexts." },
  ],
  s08: [
    { title: "Lifecycle Hook Points", rationale: "Hooks intercept at defined lifecycle points: before/after tool calls, before/after model calls, and at session start/end." },
    { title: "Chain of Responsibility", rationale: "Multiple hooks can be registered at the same point, executed in order, with the ability to short-circuit the chain." },
  ],
  s09: [
    { title: "Coordinator-Worker Pattern", rationale: "A coordinator agent manages worker agents, assigning tasks based on capabilities and collecting results." },
    { title: "Shared State via Messages", rationale: "Inter-agent communication happens through a message bus, maintaining loose coupling between agents." },
  ],
  s10: [
    { title: "Thread-Based Task Queue", rationale: "Background tasks run in separate threads, keeping the main agent loop responsive to user input." },
    { title: "Task Status Tracking", rationale: "Each background task tracks status (pending, running, completed, failed) with progress callbacks." },
  ],
  s11: [
    { title: "Session Persistence", rationale: "Session state is persisted to disk, enabling agent recovery across restarts and context continuity." },
    { title: "Memory File Format", rationale: "Memory uses a structured JSON format with typed entries for facts, preferences, and patterns learned over time." },
  ],
  s12: [
    { title: "Full Integration", rationale: "All previous mechanisms are integrated into a cohesive system with proper error handling, logging, and recovery." },
    { title: "Production Readiness", rationale: "The final agent includes health checks, graceful shutdown, and configuration management for deployment." },
  ],
};

export function DesignDecisions({ version }: DesignDecisionsProps) {
  const decisions = DESIGN_DECISIONS[version];
  if (!decisions || decisions.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Design Decisions</h3>
      <div className="space-y-3">
        {decisions.map((decision, i) => (
          <div
            key={i}
            className="rounded-lg border border-[var(--color-border)] p-4"
          >
            <h4 className="text-sm font-semibold text-[var(--color-text)]">
              {decision.title}
            </h4>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">
              {decision.rationale}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
