import { apiFetch } from "./client";

export type UserRole = "admin" | "operator";

export interface UserRead {
  id: number | string;
  email: string;
  role: UserRole;
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface UserCreate {
  email: string;
  password: string;
  role?: UserRole;
}

const AUTH_STORAGE_KEY = "authUser";
const AUTH_TOKEN_KEY = "authToken";

const buildBasicToken = (email: string, password: string) => {
  return btoa(`${email}:${password}`);
};

const saveAuthToken = (token: string) => {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
};

export function getAuthToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

const clearAuthToken = () => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
};

export function getCurrentUser(): UserRead | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as UserRead) : null;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getCurrentUser() !== null;
}

export async function login(payload: AuthRequest): Promise<UserRead> {
  const user = await apiFetch<UserRead>("/auth", {
    method: "POST",
    json: payload,
  });
  const token = buildBasicToken(payload.email, payload.password);
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
  saveAuthToken(token);
  // notify other tabs
  window.dispatchEvent(new StorageEvent("storage", { key: AUTH_STORAGE_KEY }));
  return user;
}

export function logout(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
  clearAuthToken();
  window.dispatchEvent(new StorageEvent("storage", { key: AUTH_STORAGE_KEY }));
}

export function subscribeAuth(callback: (user: UserRead | null) => void): () => void {
  const handler = (event: StorageEvent) => {
    if (event.key === AUTH_STORAGE_KEY) {
      callback(getCurrentUser());
    }
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

export interface GetUsersParams {
  limit?: number;
  offset?: number;
}

export const authHeaders = (): Record<string, string> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Требуется авторизация");
  }
  return {
    Authorization: `Basic ${token}`,
  };
};

export async function getUsers(params: GetUsersParams = {}): Promise<UserRead[]> {
  const { limit = 50, offset = 0 } = params;
  const queryParams = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  
  return apiFetch<UserRead[]>(`/users?${queryParams.toString()}`, {
    method: "GET",
    headers: authHeaders(),
  });
}

export async function createUser(payload: UserCreate): Promise<UserRead> {
  return apiFetch<UserRead>("/users", {
    method: "POST",
    json: payload,
    headers: authHeaders(),
  });
}

