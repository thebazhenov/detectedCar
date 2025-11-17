import { apiFetch } from "./client";

export interface UserRead {
  id: number | string;
  email: string;
  // add other fields from your FastAPI UserRead if needed
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface UserCreate {
  email: string;
  password: string;
}

const AUTH_STORAGE_KEY = "authUser";

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
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
  // notify other tabs
  window.dispatchEvent(new StorageEvent("storage", { key: AUTH_STORAGE_KEY }));
  return user;
}

export async function register(payload: UserCreate): Promise<UserRead> {
  const user = await apiFetch<UserRead>("/register", {
    method: "POST",
    json: payload,
  });
  // After successful registration, automatically log in the user
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
  // notify other tabs
  window.dispatchEvent(new StorageEvent("storage", { key: AUTH_STORAGE_KEY }));
  return user;
}

export function logout(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
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

export async function getUsers(params: GetUsersParams = {}): Promise<UserRead[]> {
  const { limit = 50, offset = 0 } = params;
  const queryParams = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  
  return apiFetch<UserRead[]>(`/users?${queryParams.toString()}`, {
    method: "GET",
  });
}


