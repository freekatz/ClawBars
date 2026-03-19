import React from 'react';

interface EmptyStateProps {
  message: string;
  icon?: React.ReactNode;
}

export function EmptyState({ message, icon }: EmptyStateProps) {
  return (
    <div className="w-full relative flex flex-col items-center justify-center p-12 bg-card border-4 border-black shadow-[8px_8px_0_0_#111111] overflow-hidden my-6">
      {/* Flat geometric decorations */}
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-primary/20 border-4 border-primary rounded-full pointer-events-none" />
      <div className="absolute -bottom-12 -left-8 w-24 h-24 bg-secondary/20 border-4 border-secondary rotate-12 pointer-events-none" />
      
      {/* Wavy line curve decoration */}
      <svg
        className="absolute top-1/2 left-0 w-full h-24 -translate-y-1/2 opacity-20 pointer-events-none text-accent"
        preserveAspectRatio="none"
        viewBox="0 0 1200 120"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M0,0 V46.29 C150,90.29 250,90.29 400,46.29 C550,2.29 650,2.29 800,46.29 C950,90.29 1050,90.29 1200,46.29 V0 Z"
          fill="currentColor"
          fillOpacity="0.2"
        />
        <path
          d="M0,46.29 C150,90.29 250,90.29 400,46.29 C550,2.29 650,2.29 800,46.29 C950,90.29 1050,90.29 1200,46.29"
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
        />
      </svg>
      
      {/* Zigzag decoration */}
      <svg className="absolute top-4 left-4 w-12 h-12 text-primary opacity-50 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
        <polyline points="2 12 8 4 14 20 22 10" />
      </svg>
      
      <div className="relative z-10 flex flex-col items-center gap-4 text-center">
        {icon && <div className="text-5xl text-muted-foreground bg-background p-4 border-4 border-black rounded-xl rotate-[-2deg] shadow-[4px_4px_0_0_#111111]">{icon}</div>}
        <div className="font-mono text-lg font-bold text-foreground bg-background px-4 py-2 border-2 border-black inline-block transform rotate-[1deg]">{message}</div>
      </div>
    </div>
  );
}
