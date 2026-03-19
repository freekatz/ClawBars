// api.ts
import { API_CONFIG } from "@/config/constants";
import { auth } from "./auth";
import type { ApiResponse } from "@/types/api";

export class ApiError extends Error {
  code: number;
  detail?: any;

  constructor(message: string, code: number, detail?: any) {
    super(message);
    this.code = code;
    this.detail = detail;
    this.name = "ApiError";
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

// Token refresh mutex: prevents multiple concurrent refresh attempts
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const refreshToken = auth.getRefreshToken();
      if (!refreshToken) {
        auth.clear();
        return null;
      }
      const refreshRes = await fetch(`${API_CONFIG.BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      const refreshData = await refreshRes.json().catch(() => ({}));
      if (refreshRes.ok && refreshData?.data?.access_token) {
        auth.setToken(refreshData.data.access_token);
        if (refreshData.data.refresh_token)
          auth.setRefreshToken(refreshData.data.refresh_token);
        return refreshData.data.access_token as string;
      }
      auth.clear();
      return null;
    } catch {
      auth.clear();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<ApiResponse<T>> {
  const { params, ...customConfig } = options;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  const token = auth.getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config: RequestInit = {
    ...customConfig,
    headers: {
      ...headers,
      ...customConfig.headers,
    },
  };

  let url = `${API_CONFIG.BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  let response = await fetch(url, config);
  let data = await response.json().catch(() => ({}));

  // On 401, try refresh token (skip for auth endpoints to avoid loops)
  if (response.status === 401 && !endpoint.startsWith("/auth/")) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(url, { ...config, headers });
      data = await response.json().catch(() => ({}));
    }
  }

  if (!response.ok || (data.code !== undefined && data.code !== 0)) {
    if (response.status === 401) {
      auth.clear();
    }
    const errorMessage = data.message || response.statusText || "Unknown error";
    const errorCode = data.code || response.status;
    throw new ApiError(errorMessage, errorCode, data.detail);
  }

  // Return the full ApiResponse structure
  // The backend always returns { code, message, data, meta }
  return data as ApiResponse<T>;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "GET" }),
  post: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
    }),
  put: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: JSON.stringify(body),
    }),
  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "DELETE" }),
};
