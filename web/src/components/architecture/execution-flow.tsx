"use client";
import { motion } from "framer-motion";
import type { FlowNode, FlowEdge } from "@/types/agent-data";

interface ExecutionFlowProps {
  version: string;
}

const EXECUTION_FLOWS: Record<string, { nodes: FlowNode[]; edges: FlowEdge[] }> = {
  s01: {
    nodes: [
      { id: "start", type: "start", label: "Start", x: 200, y: 0 },
      { id: "call_model", type: "process", label: "Call Model", x: 200, y: 60 },
      { id: "check_stop", type: "decision", label: "stop_reason?", x: 200, y: 140 },
      { id: "end_turn", type: "end", label: "Return Response", x: 400, y: 140 },
      { id: "parse_tools", type: "process", label: "Parse Tool Calls", x: 200, y: 220 },
      { id: "exec_tools", type: "tool", label: "Execute Tools", x: 200, y: 300 },
      { id: "append", type: "process", label: "Append Results", x: 200, y: 380 },
    ],
    edges: [
      { from: "start", to: "call_model" },
      { from: "call_model", to: "check_stop" },
      { from: "check_stop", to: "end_turn", label: "end_turn" },
      { from: "check_stop", to: "parse_tools", label: "tool_use" },
      { from: "parse_tools", to: "exec_tools" },
      { from: "exec_tools", to: "append" },
      { from: "append", to: "call_model" },
    ],
  },
  s02: {
    nodes: [
      { id: "start", type: "start", label: "Start", x: 200, y: 0 },
      { id: "call_model", type: "process", label: "Call Model", x: 200, y: 60 },
      { id: "check_stop", type: "decision", label: "stop_reason?", x: 200, y: 140 },
      { id: "end_turn", type: "end", label: "Return Response", x: 400, y: 140 },
      { id: "lookup", type: "process", label: "Lookup Tool", x: 200, y: 220 },
      { id: "validate", type: "decision", label: "Valid?", x: 200, y: 300 },
      { id: "exec", type: "tool", label: "Execute Handler", x: 100, y: 380 },
      { id: "error", type: "process", label: "Error Response", x: 350, y: 380 },
      { id: "append", type: "process", label: "Append Results", x: 100, y: 460 },
    ],
    edges: [
      { from: "start", to: "call_model" },
      { from: "call_model", to: "check_stop" },
      { from: "check_stop", to: "end_turn", label: "end_turn" },
      { from: "check_stop", to: "lookup", label: "tool_use" },
      { from: "lookup", to: "validate" },
      { from: "validate", to: "exec", label: "yes" },
      { from: "validate", to: "error", label: "no" },
      { from: "exec", to: "append" },
      { from: "error", to: "append" },
      { from: "append", to: "call_model" },
    ],
  },
};

const NODE_STYLES: Record<string, { fill: string; stroke: string; rx: number }> = {
  start: { fill: "#22c55e", stroke: "#16a34a", rx: 20 },
  process: { fill: "#3b82f6", stroke: "#2563eb", rx: 8 },
  decision: { fill: "#f59e0b", stroke: "#d97706", rx: 8 },
  tool: { fill: "#8b5cf6", stroke: "#7c3aed", rx: 8 },
  end: { fill: "#ef4444", stroke: "#dc2626", rx: 20 },
};

function getNodeForVersion(version: string) {
  if (EXECUTION_FLOWS[version]) return EXECUTION_FLOWS[version];
  // Default to s01 flow for unknown versions
  return EXECUTION_FLOWS.s01;
}

export function ExecutionFlow({ version }: ExecutionFlowProps) {
  const flow = getNodeForVersion(version);
  const { nodes, edges } = flow;

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Execution Flow</h3>
      <div className="overflow-x-auto rounded-lg border border-[var(--color-border)] bg-zinc-50 p-4 dark:bg-zinc-800/50">
        <svg
          width="500"
          height={Math.max(...nodes.map((n) => n.y)) + 80}
          viewBox={`0 0 500 ${Math.max(...nodes.map((n) => n.y)) + 80}`}
          className="mx-auto"
        >
          {/* Edges */}
          {edges.map((edge, i) => {
            const from = nodes.find((n) => n.id === edge.from);
            const to = nodes.find((n) => n.id === edge.to);
            if (!from || !to) return null;
            return (
              <g key={i}>
                <motion.line
                  x1={from.x}
                  y1={from.y + 20}
                  x2={to.x}
                  y2={to.y - 10}
                  stroke="var(--color-text-secondary)"
                  strokeWidth={1.5}
                  markerEnd="url(#arrowhead)"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ delay: i * 0.1, duration: 0.3 }}
                />
                {edge.label && (
                  <text
                    x={(from.x + to.x) / 2 + 10}
                    y={(from.y + to.y) / 2 + 5}
                    fill="var(--color-text-secondary)"
                    fontSize={10}
                    className="select-none"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Arrowhead marker */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="10"
              refY="3.5"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3.5, 0 7"
                fill="var(--color-text-secondary)"
              />
            </marker>
          </defs>

          {/* Nodes */}
          {nodes.map((node, i) => {
            const style = NODE_STYLES[node.type] || NODE_STYLES.process;
            return (
              <motion.g
                key={node.id}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05, duration: 0.2 }}
              >
                <rect
                  x={node.x - 60}
                  y={node.y - 10}
                  width={120}
                  height={30}
                  rx={style.rx}
                  fill={style.fill}
                  stroke={style.stroke}
                  strokeWidth={1.5}
                  className="dark:opacity-80"
                />
                <text
                  x={node.x}
                  y={node.y + 5}
                  textAnchor="middle"
                  fill="white"
                  fontSize={11}
                  fontWeight={500}
                  className="select-none"
                >
                  {node.label}
                </text>
              </motion.g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
