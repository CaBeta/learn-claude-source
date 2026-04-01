"use client";
import { useEffect, useState } from "react";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";
import remarkRehype from "remark-rehype";
import rehypeRaw from "rehype-raw";
import rehypeHighlight from "rehype-highlight";
import rehypeStringify from "rehype-stringify";
import docsData from "@/data/generated/docs.json";

interface DocRendererProps {
  version: string;
}

export function DocRenderer({ version }: DocRendererProps) {
  const [html, setHtml] = useState("");

  useEffect(() => {
    const doc = (docsData as any[]).find(
      (d: any) => d.version === version && d.locale === "zh"
    );
    if (!doc) {
      setHtml("<p>文档未找到</p>");
      return;
    }

    unified()
      .use(remarkParse)
      .use(remarkGfm)
      .use(remarkRehype, { allowDangerousHtml: true })
      .use(rehypeRaw)
      .use(rehypeHighlight)
      .use(rehypeStringify)
      .process(doc.content)
      .then((file) => setHtml(String(file)))
      .catch(() => setHtml("<p>渲染失败</p>"));
  }, [version]);

  return (
    <div
      className="prose-custom"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
