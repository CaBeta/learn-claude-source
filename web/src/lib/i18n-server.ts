const messages: Record<string, string> = {
  "meta.title": "从零构建 Coding Agent",
  "meta.description": "Claude Code 源码解析与实战",
  "version.tab_learn": "学习",
  "version.tab_code": "代码",
  "version.tab_deep_dive": "深入",
  "version.execution_flow": "执行流程",
  "version.architecture": "架构图",
  "version.tools": "个工具",
  "version.prev": "上一节",
  "version.next": "下一节",
};

export function getTranslations(_locale: string, namespace?: string) {
  return (key: string) => {
    const fullKey = namespace ? `${namespace}.${key}` : key;
    return messages[fullKey] || key;
  };
}
