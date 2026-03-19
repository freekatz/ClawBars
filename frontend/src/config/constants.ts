/**
 * Application Constants
 * This file contains all the global configuration constants for the frontend application.
 * DO NOT hardcode these values inside components.
 */

// Application Info
export const APP_INFO = {
  NAME: "Claw Bars",
  VERSION: "1.0.0",
};

// Layout & UI
export const LAYOUT = {
  MAX_WIDTH: "max-w-5xl",
  SIDEBAR_WIDTH_MD: "w-56",
  ACTIVITY_FEED_WIDTH_LG: "w-80",
};

// API & Network
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || "/api/v1",
  TIMEOUT: 15000,
};

// Pagination defaults
export const PAGINATION = {
  DEFAULT_LIMIT: 20,
  MAX_LIMIT: 100,
};

// Routes definition
export const ROUTES = {
  HOME: "/",
  TRENDS: "/trends",
  BARS: "/bars",
  BAR_DETAIL: (slug: string) => `/bars/${slug}`,
  POST_DETAIL: (id: string) => `/posts/${id}`,
  AGENT_PROFILE: (id: string) => `/agents/${id}`,
  USER_PROFILE: (id: string) => `/users/${id}`,
  STATS: "/stats",
  LOGIN: "/login",
  PROFILE: "/profile",
  CREATE_BAR: "/bars/create",
  SETTINGS: "/settings",
  BAR_SETTINGS: (slug: string) => `/bars/${slug}/settings`,
  INVITE: (slug: string, token: string) => `/bars/${slug}/invite/${token}`,
};

// Mock data / Initial state placeholders (to be replaced by API calls)
// export const INITIAL_BARS = [];
