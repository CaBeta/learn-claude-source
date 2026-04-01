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
