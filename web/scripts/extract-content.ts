import * as fs from "fs";
import * as path from "path";

const AGENTS_DIR = path.resolve(__dirname, "../../agents");
const DOCS_DIR = path.resolve(__dirname, "../../docs/zh");
const OUTPUT_DIR = path.resolve(__dirname, "../src/data/generated");

interface AgentVersion {
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

interface DocContent {
  version: string;
  locale: string;
  title: string;
  content: string;
}

function extractClasses(source: string): string[] {
  const matches = source.match(/^class\s+(\w+)/gm) || [];
  return matches.map((m) => m.replace("class ", ""));
}

function extractFunctions(source: string): string[] {
  const matches = source.match(/^(?:async\s+)?def\s+(\w+)/gm) || [];
  return matches.map((m) => m.replace(/^(?:async\s+)?def\s+/, ""));
}

function extractTools(source: string): string[] {
  const tools: string[] = [];
  const regex = /"name":\s*"(\w+)"/g;
  let match;
  while ((match = regex.exec(source)) !== null) {
    if (!tools.includes(match[1])) tools.push(match[1]);
  }
  return tools;
}

function getLayer(id: string): string {
  const num = parseInt(id.replace("s", ""));
  if (num <= 3) return "core";
  if (num <= 6) return "intelligence";
  if (num <= 9) return "extension";
  return "production";
}

function processAgents(): { versions: AgentVersion[]; diffs: any[] } {
  const versions: AgentVersion[] = [];
  const files = fs.readdirSync(AGENTS_DIR).filter((f) => f.endsWith(".py")).sort();
  const versionMeta: Record<string, Partial<AgentVersion>> = {
    s01: { title: "Agent Loop", subtitle: "while(true) — 代理的核心循环", coreAddition: "while(true) loop", keyInsight: "一切始于一个循环" },
    s02: { title: "Tool Use", subtitle: "dispatch map — 给代理装上双手", coreAddition: "工具注册 + 执行", keyInsight: "给它手，它才能干活" },
    s03: { title: "Streaming", subtitle: "token-by-token — 实时输出", coreAddition: "流式响应", keyInsight: "流式输出让用户看到思考的过程" },
    s04: { title: "SubAgent", subtitle: "子代理派发与回收", coreAddition: "spawn_subagent()", keyInsight: "大任务拆小" },
    s05: { title: "Context Mgmt", subtitle: "5层上下文压缩", coreAddition: "上下文管理管线", keyInsight: "聪明的代理知道该忘记什么" },
    s06: { title: "Permission", subtitle: "6种权限模式", coreAddition: "权限检查管线", keyInsight: "信任但验证" },
    s07: { title: "Skills", subtitle: "可复用技能模板", coreAddition: "SkillLoader + SkillManager", keyInsight: "一次学会，终身受用" },
    s08: { title: "Hooks", subtitle: "生命周期拦截器", coreAddition: "HookManager + Pre/Post hooks", keyInsight: "在每个关键时刻介入" },
    s09: { title: "Multi-Agent", subtitle: "多代理协调器", coreAddition: "Coordinator + Worker", keyInsight: "一群人走得远" },
    s10: { title: "Background Tasks", subtitle: "异步任务管理", coreAddition: "TaskQueue + threading", keyInsight: "后台执行，前台响应" },
    s11: { title: "Session Memory", subtitle: "跨会话持久记忆", coreAddition: "MemoryFile + SessionStore", keyInsight: "记住过去，才能规划未来" },
    s12: { title: "Production Agent", subtitle: "完整生产级代理", coreAddition: "全机制整合", keyInsight: "从原型到产品" },
  };

  for (const file of files) {
    const id = file.replace("_", "-").split("-")[0];
    const source = fs.readFileSync(path.join(AGENTS_DIR, file), "utf-8");
    const meta = versionMeta[id] || {};
    const prevTools = versions.length > 0 ? versions[versions.length - 1].tools : [];
    const currentTools = extractTools(source);
    const newTools = currentTools.filter((t) => !prevTools.includes(t));

    versions.push({
      id,
      filename: file,
      title: (meta as any).title || id,
      subtitle: (meta as any).subtitle || "",
      loc: source.split("\n").length,
      tools: currentTools,
      newTools,
      coreAddition: (meta as any).coreAddition || "",
      keyInsight: (meta as any).keyInsight || "",
      classes: extractClasses(source),
      functions: extractFunctions(source),
      layer: getLayer(id),
      source,
    });
  }

  const diffs = [];
  for (let i = 1; i < versions.length; i++) {
    const prev = versions[i - 1];
    const curr = versions[i];
    diffs.push({
      from: prev.id,
      to: curr.id,
      newClasses: curr.classes.filter((c) => !prev.classes.includes(c)),
      newFunctions: curr.functions.filter((f) => !prev.functions.includes(f)),
      newTools: curr.newTools,
      locDelta: curr.loc - prev.loc,
    });
  }

  return { versions, diffs };
}

function processDocs(): DocContent[] {
  const docs: DocContent[] = [];
  if (!fs.existsSync(DOCS_DIR)) return docs;

  const files = fs.readdirSync(DOCS_DIR).filter((f) => f.endsWith(".md")).sort();
  for (const file of files) {
    const content = fs.readFileSync(path.join(DOCS_DIR, file), "utf-8");
    const id = file.replace(".md", "").split("-")[0];
    const titleMatch = content.match(/^#\s+(.+)$/m);
    docs.push({
      version: id,
      locale: "zh",
      title: titleMatch ? titleMatch[1] : id,
      content,
    });
  }
  return docs;
}

// Main
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const { versions, diffs } = processAgents();
const docs = processDocs();

fs.writeFileSync(path.join(OUTPUT_DIR, "versions.json"), JSON.stringify({ versions, diffs }, null, 2));
fs.writeFileSync(path.join(OUTPUT_DIR, "docs.json"), JSON.stringify(docs, null, 2));

console.log(`Extracted ${versions.length} versions, ${docs.length} docs`);
