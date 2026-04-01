"use client";
import { createContext, useContext } from "react";

type Messages = Record<string, string>;

const messages: Messages = {
  "meta.title": "从零构建 Coding Agent",
  "meta.description": "Claude Code 源码解析与实战",
  "nav.home": "首页",
  "nav.learn": "课程",
  "home.hero_title": "从零构建 Coding Agent",
  "home.hero_subtitle": "Claude Code 源码解析与实战 — 12 个 Session，从 while(True) 到生产级 Agent",
  "home.start": "开始学习 →",
  "home.core_pattern": "核心模式",
  "home.core_pattern_desc": "Agent Loop — 一个会思考的循环",
  "home.message_flow": "消息流",
  "home.message_flow_desc": "Agent 与 Model 之间的消息交互",
  "home.learning_path": "学习路径",
  "home.learning_path_desc": "12 个 Session，4 个阶段，逐步构建完整 Agent",
  "home.loc": "行代码",
  "home.layers_title": "四个阶段",
  "home.layers_desc": "从核心循环到生产级代理",
  "home.versions_in_layer": "个 Session",
  "version.tab_learn": "学习",
  "version.tab_code": "代码",
  "version.tab_deep_dive": "深入",
  "version.execution_flow": "执行流程",
  "version.architecture": "架构图",
  "version.tools": "个工具",
  "version.prev": "上一节",
  "version.next": "下一节",
};

const I18nContext = createContext({ locale: "zh", messages });

export function I18nProvider({ locale, children }: { locale: string; children: React.ReactNode }) {
  return (
    <I18nContext.Provider value={{ locale, messages }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslations(namespace?: string) {
  const { messages } = useContext(I18nContext);
  return (key: string) => {
    const fullKey = namespace ? `${namespace}.${key}` : key;
    return messages[fullKey] || key;
  };
}

export function useLocale() {
  const { locale } = useContext(I18nContext);
  return locale;
}
