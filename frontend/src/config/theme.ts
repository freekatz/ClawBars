/**
 * Theme configuration and utilities
 * ClawBars Design System - AI Agent Intelligence Exchange
 * Style: Vibrant, Dynamic, Tech-Forward
 * Palette: Neon Azure + Luminous Violet + Electric Cyan
 */

export const theme = {
  colors: {
    // Brand colors (CSS variable references)
    primary: "var(--primary)",
    primaryHover: "var(--primary-hover)",
    secondary: "var(--secondary)",
    secondaryHover: "var(--secondary-hover)",
    accent: "var(--accent)",
    accentHover: "var(--accent-hover)",

    // Semantic colors
    background: "var(--background)",
    foreground: "var(--foreground)",
    card: "var(--card)",
    cardHover: "var(--card-hover)",
    border: "var(--border)",
    borderHover: "var(--border-hover)",
    muted: "var(--muted)",
    mutedForeground: "var(--muted-foreground)",

    // Status colors
    destructive: "var(--destructive)",
    destructiveMuted: "var(--destructive-muted)",
    success: "var(--success)",
    successMuted: "var(--success-muted)",
    warning: "var(--warning)",
    warningMuted: "var(--warning-muted)",
    info: "var(--info)",
    infoMuted: "var(--info-muted)",

    // Gradient
    gradientStart: "var(--gradient-start)",
    gradientMid: "var(--gradient-mid)",
    gradientEnd: "var(--gradient-end)",
  },

  // Reusable classes for components
  classes: {
    // Background and Cards
    glassCard: "glass hover:border-border-hover transition-all duration-300",
    glassPanel: "glass backdrop-blur-2xl",

    // Borders & Glows
    glowPrimary: "shadow-[var(--shadow-glow-primary)] border-primary/40",
    glowSecondary: "shadow-[var(--shadow-glow-secondary)] border-secondary/40",
    glowAccent: "shadow-[var(--shadow-glow-accent)] border-accent/40",

    // Gradient Effects
    gradientPrimary: "gradient-primary",
    gradientText: "gradient-text",
    gradientBorder: "gradient-border",

    // Text Effects
    textGlowPrimary: "text-primary text-glow-primary",
    textGlowSecondary: "text-secondary text-glow-secondary",
    textGlowAccent: "text-accent text-glow-accent",

    // Interactive
    hoverLift: "hover-lift",
    hoverGlow: "hover-glow",

    // Typography
    fontDisplay: "font-display tracking-tight",
    fontMono: "font-mono",
    fontSans: "font-sans",
  },

  // Animation timing
  transitions: {
    fast: "var(--transition-fast)",
    base: "var(--transition-base)",
    slow: "var(--transition-slow)",
  },

  // Spacing
  spacing: {
    xs: "var(--space-1)",
    sm: "var(--space-2)",
    md: "var(--space-3)",
    lg: "var(--space-4)",
    xl: "var(--space-6)",
    "2xl": "var(--space-8)",
  },
};

// Color variants for component props
export type ColorVariant =
  | "primary"
  | "secondary"
  | "accent"
  | "neutral"
  | "success"
  | "destructive";
export type SizeVariant = "sm" | "md" | "lg";

export default theme;
