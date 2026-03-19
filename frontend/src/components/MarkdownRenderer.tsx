import { useEffect, useRef, useId } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "neutral",
  securityLevel: "strict",
  fontFamily: "JetBrains Mono, monospace",
});

function MermaidBlock({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId().replace(/:/g, "_");

  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    el.innerHTML = "";
    mermaid
      .render(`mermaid${id}`, code)
      .then(({ svg }) => {
        el.innerHTML = svg;
      })
      .catch(() => {
        el.innerHTML = `<pre class="text-destructive text-xs">${code}</pre>`;
      });
  }, [code, id]);

  return <div ref={ref} className="my-4 flex justify-center overflow-x-auto" />;
}

interface MarkdownRendererProps {
  content: string;
  className?: string;
  compact?: boolean;
}

export default function MarkdownRenderer({
  content,
  className = "",
  compact = false,
}: MarkdownRendererProps) {
  return (
    <div
      className={`markdown-body ${compact ? "markdown-compact" : ""} ${className}`}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code({ className: codeClassName, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClassName || "");
            const lang = match?.[1];
            const codeStr = String(children).replace(/\n$/, "");

            if (lang === "mermaid") {
              return <MermaidBlock code={codeStr} />;
            }

            if (lang) {
              return (
                <div className="relative my-4">
                  <div className="absolute top-0 left-0 px-2 py-0.5 text-[10px] font-mono font-bold uppercase bg-border text-muted-foreground border-b-2 border-r-2 border-border">
                    {lang}
                  </div>
                  <pre className="bg-muted border-4 border-border p-4 pt-8 overflow-x-auto text-sm font-mono shadow-[2px_2px_0_0_var(--color-border)]">
                    <code className={codeClassName} {...props}>
                      {children}
                    </code>
                  </pre>
                </div>
              );
            }

            return (
              <code
                className="bg-muted px-1.5 py-0.5 border-2 border-border text-sm font-mono font-bold text-primary"
                {...props}
              >
                {children}
              </code>
            );
          },
          pre({ children }) {
            return <>{children}</>;
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-4">
                <table className="w-full border-4 border-border text-sm font-mono">
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="bg-muted border-2 border-border px-3 py-2 text-left font-black uppercase text-xs tracking-wider">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="border-2 border-border px-3 py-2">{children}</td>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-primary pl-4 my-4 text-muted-foreground italic">
                {children}
              </blockquote>
            );
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline underline-offset-2 hover:text-primary/80 transition-colors"
              >
                {children}
              </a>
            );
          },
          img({ src, alt }) {
            return (
              <img
                src={src}
                alt={alt || ""}
                className="max-w-full rounded border-4 border-border shadow-[2px_2px_0_0_var(--color-border)] my-4"
              />
            );
          },
          hr() {
            return <hr className="border-t-4 border-border my-6" />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
