// Simple API client for FastAPI backend
// In development, use /api proxy (configured in vite.config.ts)
// In production, use environment variable or full URL
const DEFAULT_BASE_URL = import.meta.env.DEV ? "/api" : "http://localhost:8000";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL;

export async function apiFetch<TResponse>(
  path: string,
  options: RequestInit & { json?: unknown } = {}
): Promise<TResponse> {
  const url = `${apiBaseUrl}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
    body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
  });

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await response.json() : (null as unknown as TResponse);

  if (!response.ok) {
    const message =
      (isJson && (data as any)?.detail) ||
      (isJson && (data as any)?.message) ||
      response.statusText ||
      "Request failed";
    const error = new Error(message);
    // Attach status code for error handling
    (error as any).status = response.status;
    throw error;
  }

  return data as TResponse;
}

export { apiBaseUrl };


