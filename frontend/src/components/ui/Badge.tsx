import React from 'react';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'neutral' | 'success' | 'destructive';
  /** Legacy prop aliases */
  color?: 'cyan' | 'magenta' | 'amber' | 'neutral';
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = '', variant, color, children, ...props }, ref) => {

    // Support legacy 'color' prop by mapping to new variants
    const resolvedVariant = variant || (color === 'cyan' ? 'primary' : color === 'magenta' ? 'secondary' : color === 'amber' ? 'accent' : color) || 'primary';

    const getVariantClass = () => {
      switch (resolvedVariant) {
        case 'primary':
          return 'bg-primary/10 text-primary border border-primary/30';
        case 'secondary':
          return 'bg-secondary/30 text-secondary-foreground border border-secondary/50';
        case 'accent':
          return 'bg-accent/10 text-accent border border-accent/30';
        case 'success':
          return 'bg-success/10 text-success border border-success/30';
        case 'destructive':
          return 'bg-destructive/10 text-destructive border border-destructive/30';
        case 'neutral':
        default:
          return 'bg-muted text-muted-foreground border border-border';
      }
    };

    return (
      <span
        ref={ref}
        className={`inline-flex items-center px-2 py-0.5 rounded text-[var(--text-xs)] font-mono font-medium ${getVariantClass()} ${className}`}
        {...props}
      >
        {children}
      </span>
    );
  }
);
Badge.displayName = 'Badge';