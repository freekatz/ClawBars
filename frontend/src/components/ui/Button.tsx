import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "accent" | "ghost" | "danger";
  size?: "sm" | "md" | "lg" | "icon";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className = "", variant = "primary", size = "md", children, ...props },
    ref,
  ) => {
    const getVariantClass = () => {
      switch (variant) {
        case "primary":
          return "bg-primary text-primary-foreground font-bold hover:bg-primary-hover border-2 border-border active:translate-y-0.5";
        case "secondary":
          return "bg-secondary text-secondary-foreground font-bold hover:bg-secondary-hover border-2 border-border active:translate-y-0.5";
        case "accent":
          return "bg-accent text-accent-foreground font-bold hover:bg-accent-hover border-2 border-border active:translate-y-0.5";
        case "ghost":
          return "bg-transparent text-foreground font-bold hover:bg-muted border-2 border-transparent hover:border-border active:translate-y-0.5";
        case "danger":
          return "bg-destructive text-destructive-foreground font-bold hover:bg-destructive/80 border-2 border-border active:translate-y-0.5";
        default:
          return "";
      }
    };

    const getSizeClass = () => {
      switch (size) {
        case "sm":
          return "px-2 py-1 text-[var(--text-xs)] rounded-[var(--radius-sm)]";
        case "md":
          return "px-3 py-1.5 text-[var(--text-sm)] rounded-[var(--radius-md)]";
        case "lg":
          return "px-4 py-2 text-[var(--text-base)] rounded-[var(--radius-md)]";
        case "icon":
          return "p-2 flex items-center justify-center min-w-[36px] min-h-[36px] rounded-[var(--radius-md)]";
        default:
          return "px-3 py-1.5 text-[var(--text-sm)] rounded-[var(--radius-md)]";
      }
    };

    return (
      <button
        ref={ref}
        className={`inline-flex items-center justify-center font-sans transition-all duration-[var(--transition-base)] disabled:opacity-50 disabled:pointer-events-none focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background ${getVariantClass()} ${getSizeClass()} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";
