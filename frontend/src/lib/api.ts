/**
 * Thin client for the SmartDocZ FastAPI backend.
 *
 * Every request carries the Clerk session token as a Bearer credential, which
 * the backend validates (see backend/app/auth.py). Obtain the token on the
 * client with `useAuth().getToken()` and pass it in.
 */
const BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export interface ApiUser {
  id: string;
  clerk_user_id: string;
  email: string | null;
  full_name: string | null;
  created_at: string;
  updated_at: string;
}

async function request<T>(
  path: string,
  token: string | null,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health", null),
  me: (token: string) => request<ApiUser>("/me", token),
};
