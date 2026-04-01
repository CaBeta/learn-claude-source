export interface AgentVersion {
  id: string;
  filename: string;
  title: string;
  subtitle: string;
  loc: number;
  tools: string[];
  newTools: string[];
  coreAddition: string;
  keyInsight: string;
  classes: string[];
  functions: string[];
  layer: string;
  source: string;
}

export interface VersionDiff {
  from: string;
  to: string;
  newClasses: string[];
  newFunctions: string[];
  newTools: string[];
  locDelta: number;
}

export interface DocContent {
  version: string;
  locale: string;
  title: string;
  content: string;
}

export type SimStepType =
  | "think"
  | "tool_call"
  | "tool_result"
  | "user_input"
  | "system"
  | "response"
  | "decision"
  | "error";

export interface SimStep {
  type: SimStepType;
  label: string;
  detail: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: string;
  duration?: number;
}

export interface Scenario {
  version: string;
  title: string;
  description: string;
  steps: SimStep[];
}

export interface FlowNode {
  id: string;
  type: "start" | "process" | "decision" | "tool" | "end";
  label: string;
  x: number;
  y: number;
}

export interface FlowEdge {
  from: string;
  to: string;
  label?: string;
}

export interface VersionIndex {
  versions: AgentVersion[];
  diffs: VersionDiff[];
}
