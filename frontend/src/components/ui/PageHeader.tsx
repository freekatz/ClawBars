import React from "react";

interface PageHeaderProps {
  title: string;
  badge?: string;
  statusText?: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

export function PageHeader({
  title,
  badge,
  statusText,
  icon,
  children,
}: PageHeaderProps) {
  return (
    <header className="relative flex flex-col md:flex-row md:items-end justify-between gap-4 border-b-4 border-border pb-5 mb-8">
      <div className="space-y-1.5">
        {badge && (
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-primary text-primary-foreground font-mono text-[9px] font-bold uppercase tracking-widest rotate-[-1deg]">
            <span className="w-1.5 h-1.5 bg-primary-foreground animate-ping rounded-full" />
            {badge}
          </div>
        )}
        <div className="flex items-center gap-3">
          {icon && <div className="text-primary">{icon}</div>}
          <h1 className="text-3xl md:text-4xl font-black font-display text-foreground uppercase italic tracking-tighter">
            {title}
          </h1>
        </div>
      </div>

      <div className="flex flex-col md:items-end gap-3">
        {statusText && (
          <div className="bg-foreground text-background p-2 border-2 border-border shadow-[2px_2px_0_0_var(--color-accent)] font-mono text-[10px] rotate-[1deg] whitespace-nowrap">
            {statusText}
          </div>
        )}
        {children && <div className="flex items-center gap-2">{children}</div>}
      </div>

      {/* Decorative pulse line (optional/subtle) */}
      <div className="absolute -bottom-1 left-0 w-full h-[2px] bg-primary/20 overflow-hidden">
        <div className="w-20 h-full bg-primary animate-scroll-ticker" />
      </div>
    </header>
  );
}
