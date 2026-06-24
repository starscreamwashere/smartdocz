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

export interface ApiSession {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
}

export interface ApiSessionSummary extends ApiSession {
  message_count: number;
  file_count: number;
}

export interface ApiFile {
  id: string;
  session_id: string;
  filename: string;
  file_type: string;
  file_size_mb: number | null;
  upload_status: string;
  created_at: string;
}

export interface UploadResult {
  file: ApiFile;
  session_id: string;
  chunks_stored: number;
}

export interface Source {
  page_number: number;
  chunk_index: number;
  snippet: string;
}

export interface ChatResult {
  session_id: string;
  message_id: string;
  answer: string;
  sources: Source[];
  has_context: boolean;
  model_provider: string;
  model: string;
}

export interface ApiMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model_provider: string | null;
  created_at: string;
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
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

async function uploadRequest<T>(
  path: string,
  token: string,
  form: FormData,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` }, // no Content-Type: let the browser set the multipart boundary
    body: form,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health", null),
  me: (token: string) => request<ApiUser>("/me", token),

  upload: (token: string, file: File, sessionId?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (sessionId) form.append("session_id", sessionId);
    return uploadRequest<UploadResult>("/upload", token, form);
  },

  uploadYoutube: (token: string, youtubeUrl: string, sessionId?: string) => {
    const form = new FormData();
    form.append("youtube_url", youtubeUrl);
    if (sessionId) form.append("session_id", sessionId);
    return uploadRequest<UploadResult>("/upload", token, form);
  },

  chat: (token: string, sessionId: string, message: string) =>
    request<ChatResult>("/chat", token, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message }),
    }),

  messages: (token: string, sessionId: string) =>
    request<ApiMessage[]>(`/messages/${sessionId}`, token),

  listSessions: (token: string) =>
    request<ApiSessionSummary[]>("/sessions", token),

  getSession: (token: string, sessionId: string) =>
    request<ApiSession>(`/sessions/${sessionId}`, token),

  deleteSession: (token: string, sessionId: string) =>
    request<void>(`/sessions/${sessionId}`, token, { method: "DELETE" }),
};
