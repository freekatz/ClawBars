import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glowColor?: 'primary' | 'secondary' | 'accent' | 'none';
  variant?: 'glass' | 'solid';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', glowColor = 'none', variant = 'glass', children, ...props }, ref) => {

    const getGlowClass = () => {
      switch (glowColor) {
        case 'primary':
          return 'hover:-translate-y-1 hover:border-primary';
        case 'secondary':
          return 'hover:-translate-y-1 hover:border-secondary';
        case 'accent':
          return 'hover:-translate-y-1 hover:border-accent';
        default:
          return 'hover:-translate-y-1';
      }
    };

    const baseClass = variant === 'glass'
      ? 'glass'
      : 'card-base';

    return (
      <div
        ref={ref}
        className={`p-4 transition-all duration-[var(--transition-fast)] ${baseClass} ${getGlowClass()} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = 'Card';