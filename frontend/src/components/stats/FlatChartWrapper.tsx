import React from "react";

interface FlatChartWrapperProps {
  title: string;
  children: React.ReactNode;
}

export function FlatChartWrapper({ title, children }: FlatChartWrapperProps) {
  return (
    <div className="bg-card border-2 border-black p-4 shadow-[2px_2px_0_0_#111111] relative overflow-hidden group hover:shadow-[3px_3px_0_0_#111111] transition-all">
      {/* Decorative background grid */}
      <div className="absolute top-0 right-0 w-16 h-16 bg-primary/5 pointer-events-none -rotate-12 transform translate-x-6 -translate-y-6 border-2 border-primary/10" />

      <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-primary mb-4 flex items-center gap-1.5">
        <span className="w-2 h-2 bg-primary rotate-45 inline-block" />
        {title}
      </h3>

      <div className="w-full h-52 min-h-[208px]">{children}</div>

      <div className="absolute bottom-1.5 right-1.5 flex gap-0.5 pointer-events-none">
        <div className="w-1 h-1 bg-border" />
        <div className="w-1 h-1 bg-border" />
        <div className="w-1 h-1 bg-border" />
      </div>
    </div>
  );
}
