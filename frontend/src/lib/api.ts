import { AnalysisJob, Dashboard, DocumentItem, DocumentVersion, MetricsStatus, Paginated, RAGAnswer, SafetyStatus, User, Workspace, WorkspaceMember } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const ROOT_API_URL = API_URL.replace(/\/api\/v1\/?$/, "");
const TOKEN_KEY = "kbm_token";

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail ?? "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

async function rootRequest<T>(path: string): Promise<T> {
  const response = await fetch(`${ROOT_API_URL}${path}`);
  if (!response.ok) throw new Error("System status request failed");
  return response.json();
}

type RAGStreamHandlers = {
  onStatus?: (message: string) => void;
  onCitations?: (citations: RAGAnswer["citations"]) => void;
  onToken?: (text: string) => void;
};

async function streamRequest(path: string, body: unknown, handlers: RAGStreamHandlers): Promise<RAGAnswer> {
  const token = getToken();
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
  if (!response.ok || !response.body) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail ?? "Request failed");
  }

  const decoder = new TextDecoder();
  const reader = response.body.getReader();
  let buffer = "";
  let answer = "";
  let citations: RAGAnswer["citations"] = [];

  function consume(rawEvent: string) {
    const event = rawEvent.match(/^event: (.+)$/m)?.[1];
    const data = rawEvent.match(/^data: (.+)$/m)?.[1];
    if (!event || !data) return;
    const payload = JSON.parse(data) as { message?: string; citations?: RAGAnswer["citations"]; text?: string; answer?: string };
    if (event === "status" && payload.message) handlers.onStatus?.(payload.message);
    if (event === "citations" && payload.citations) {
      citations = payload.citations;
      handlers.onCitations?.(citations);
    }
    if (event === "token" && payload.text) {
      answer += payload.text;
      handlers.onToken?.(payload.text);
    }
    if (event === "done" && typeof payload.answer === "string") answer = payload.answer;
  }

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    events.filter(Boolean).forEach(consume);
  }
  if (buffer.trim()) consume(buffer);
  return { answer, citations };
}

export function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    }),
  register: (name: string, email: string, password: string) =>
    request<{ access_token: string; user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password })
    }),
  me: () => request<User>("/auth/me"),
  dashboard: () => request<Dashboard>("/dashboard"),
  workspaces: () => request<Workspace[]>("/workspaces"),
  createWorkspace: (name: string, description: string) =>
    request<Workspace>("/workspaces", { method: "POST", body: JSON.stringify({ name, description }) }),
  updateWorkspace: (id: string, payload: { name?: string; description?: string }) =>
    request<Workspace>(`/workspaces/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  exportWorkspace: (id: string) => request(`/workspaces/${id}/export`),
  createCollection: (workspace_id: string, name: string) =>
    request("/collections", { method: "POST", body: JSON.stringify({ workspace_id, name }) }),
  createNote: (payload: { workspace_id: string; title: string; content: string; tags: string[]; collection_ids: string[] }) =>
    request<DocumentItem>("/documents/notes", { method: "POST", body: JSON.stringify(payload) }),
  uploadDocument: (form: FormData) => request<DocumentItem>("/documents/upload", { method: "POST", body: form }),
  document: (id: string) => request<DocumentItem>(`/documents/${id}`),
  search: async (q: string) => {
    const result = await request<Paginated<DocumentItem>>(`/dashboard/search?q=${encodeURIComponent(q)}`);
    return result.items;
  },
  regenerate: (id: string) => request<DocumentItem>(`/documents/${id}/analyze`, { method: "POST" }),
  archiveDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  restoreDocument: (id: string) => request<DocumentItem>(`/documents/${id}/restore`, { method: "POST" }),
  exportDocument: (id: string) => request(`/documents/${id}/export`),
  analysisJobs: (id: string) => request<AnalysisJob[]>(`/documents/${id}/analysis-jobs`),
  versions: (id: string) => request<DocumentVersion[]>(`/documents/${id}/versions`),
  restoreVersion: (id: string, version: number) =>
    request<DocumentItem>(`/documents/${id}/versions/${version}/restore`, { method: "POST" }),
  members: (workspaceId: string) => request<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`),
  addMember: (workspaceId: string, email: string, role: WorkspaceMember["role"]) =>
    request<WorkspaceMember>(`/workspaces/${workspaceId}/members`, {
      method: "POST",
      body: JSON.stringify({ email, role })
    }),
  workspaceDocuments: (workspaceId: string, includeArchived = false) =>
    request<Paginated<DocumentItem>>(`/workspaces/${workspaceId}/documents?include_archived=${includeArchived}`),
  ask: (query: string, limit = 5) =>
    request<RAGAnswer>("/rag/query", { method: "POST", body: JSON.stringify({ query, limit }) }),
  askStream: (query: string, handlers: RAGStreamHandlers, limit = 5) =>
    streamRequest("/rag/query/stream", { query, limit }, handlers),
  sendRagFeedback: (payload: { query: string; answer: string; rating: "helpful" | "not_helpful"; comment?: string; citations: RAGAnswer["citations"] }) =>
    request("/rag/feedback", { method: "POST", body: JSON.stringify(payload) }),
  health: () => rootRequest<{ status: string }>("/health"),
  ready: () => rootRequest<{ status: string }>("/ready"),
  safety: () => rootRequest<SafetyStatus>("/safety"),
  metrics: () => rootRequest<MetricsStatus>("/metrics.json")
};
