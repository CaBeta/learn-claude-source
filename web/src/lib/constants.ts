export const VERSION_ORDER = [
  "s01", "s02", "s03", "s04", "s05", "s06",
  "s07", "s08", "s09", "s10", "s11", "s12",
] as const;

export type VersionId = (typeof VERSION_ORDER)[number];

export const VERSION_META: Record<
  string,
  {
    title: string;
    subtitle: string;
    coreAddition: string;
    keyInsight: string;
    layer: string;
  }
> = {
  s01: {
    title: "Agent Loop",
    subtitle: "while(true) — 代理的核心循环",
    coreAddition: "while(true) loop",
    keyInsight: "一切始于一个循环 — call model, check stop, repeat",
    layer: "core",
  },
  s02: {
    title: "Tool Use",
    subtitle: "dispatch map — 给代理装上双手",
    coreAddition: "工具注册 + 执行",
    keyInsight: "没有工具的代理只是聊天机器人 — 给它手，它才能干活",
    layer: "core",
  },
  s03: {
    title: "Streaming",
    subtitle: "token-by-token — 实时输出",
    coreAddition: "流式响应",
    keyInsight: "等待是毒药 — 流式输出让用户看到思考的过程",
    layer: "core",
  },
  s04: {
    title: "SubAgent",
    subtitle: "子代理派发与回收",
    coreAddition: "spawn_subagent()",
    keyInsight: "大任务拆小 — 每个子任务获得干净的上下文",
    layer: "intelligence",
  },
  s05: {
    title: "Context Mgmt",
    subtitle: "5层上下文压缩",
    coreAddition: "上下文管理管线",
    keyInsight: "记忆是有限的 — 聪明的代理知道该忘记什么",
    layer: "intelligence",
  },
  s06: {
    title: "Permission",
    subtitle: "6种权限模式",
    coreAddition: "权限检查管线",
    keyInsight: "信任但验证 — 每个工具调用都需要通过安全检查",
    layer: "intelligence",
  },
  s07: {
    title: "Skills",
    subtitle: "可复用技能模板",
    coreAddition: "SkillLoader + SkillManager",
    keyInsight: "一次学会，终身受用 — 技能让代理拥有专业能力",
    layer: "extension",
  },
  s08: {
    title: "Hooks",
    subtitle: "生命周期拦截器",
    coreAddition: "HookManager + Pre/Post hooks",
    keyInsight: "在每个关键时刻介入 — 钩子让你定制代理的每个行为",
    layer: "extension",
  },
  s09: {
    title: "Multi-Agent",
    subtitle: "多代理协调器",
    coreAddition: "Coordinator + Worker",
    keyInsight: "一个人走得快，一群人走得远 — 协调器指挥代理团队",
    layer: "extension",
  },
  s10: {
    title: "Background Tasks",
    subtitle: "异步任务管理",
    coreAddition: "TaskQueue + threading",
    keyInsight: "不让用户等待 — 后台执行，前台响应",
    layer: "production",
  },
  s11: {
    title: "Session Memory",
    subtitle: "跨会话持久记忆",
    coreAddition: "MemoryFile + SessionStore",
    keyInsight: "记住过去，才能规划未来 — 会话记忆让代理持续进化",
    layer: "production",
  },
  s12: {
    title: "Production Agent",
    subtitle: "完整生产级代理",
    coreAddition: "全机制整合",
    keyInsight: "从原型到产品 — 一个完整的生产级 Coding Agent",
    layer: "production",
  },
};

export const LEARNING_PATH = VERSION_ORDER;

export const LAYERS = [
  { id: "core", label: "CORE LOOP", color: "#3b82f6", versions: ["s01", "s02", "s03"] },
  { id: "intelligence", label: "INTELLIGENCE", color: "#10b981", versions: ["s04", "s05", "s06"] },
  { id: "extension", label: "EXTENSION", color: "#f59e0b", versions: ["s07", "s08", "s09"] },
  { id: "production", label: "PRODUCTION", color: "#ef4444", versions: ["s10", "s11", "s12"] },
];
