export type User = { id: string; email: string; name: string };

export type Workspace = {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
};

export type Collection = {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  document_count?: number;
};

export type DocumentItem = {
  id: string;
  workspace_id: string;
  title: string;
  source_type: string;
  filename?: string;
  file_storage_path?: string;
  file_size_bytes?: number;
  analysis_status: "pending" | "running" | "complete" | "failed";
  archived_at?: string | null;
  content: string;
  content_segments?: Array<{ text: string; page_number?: number | null; paragraph_index?: number }>;
  summary?: string;
  key_points: string[];
  action_items: string[];
  collection_ids: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type Paginated<T> = {
  items: T[];
  total?: number;
  limit: number;
  offset: number;
};

export type Dashboard = {
  workspaces: Workspace[];
  collections: Collection[];
  recent_documents: DocumentItem[];
  insights: Array<{
    document_id: string;
    title: string;
    summary?: string;
    key_points: string[];
    action_items: string[];
  }>;
  activity: Array<{ id: string; action: string; message: string; created_at: string }>;
  rag_feedback?: { helpful: number; not_helpful: number; total: number };
};

export type ActivityItem = {
  id: string;
  workspace_id: string;
  actor_id: string;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  message: string;
  created_at: string;
};

export type RAGAnswer = {
  answer: string;
  citations: Array<{
    document_id: string;
    workspace_id?: string;
    document_title: string;
    chunk_index: number;
    source_refs?: Array<{ label?: string; page_number?: number | null; paragraph_index?: number }>;
    text: string;
  }>;
};

export type RAGFeedbackItem = {
  id: string;
  user_id: string;
  workspace_ids: string[];
  query: string;
  answer: string;
  rating: "helpful" | "not_helpful";
  comment?: string | null;
  citations: RAGAnswer["citations"];
  created_at: string;
  updated_at: string;
};

export type WorkspaceMember = {
  id: string;
  workspace_id: string;
  user_id: string;
  email: string;
  name: string;
  role: "owner" | "editor" | "viewer";
};

export type AnalysisJob = {
  id: string;
  workspace_id: string;
  document_id: string;
  requested_by: string;
  status: "running" | "complete" | "failed";
  error?: string;
  created_at: string;
  updated_at: string;
};

export type DocumentVersion = {
  id: string;
  workspace_id: string;
  document_id: string;
  version: number;
  actor_id: string;
  reason: string;
  snapshot: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SafetyStatus = {
  zero_cost_mode: boolean;
  ai_provider: string;
  embedding_provider: string;
  openai_key_configured: boolean;
  paid_ai_blocked: boolean;
  paid_embeddings_blocked: boolean;
  billing_risk: boolean;
};

export type MetricsStatus = {
  uptime_seconds: number;
  total_requests: number;
  in_flight: number;
  average_latency_ms: number;
  status_counts: Record<string, number>;
  method_counts: Record<string, number>;
  path_counts: Record<string, number>;
  recent_errors: Array<{ method: string; path: string; status_code: number; elapsed_ms: number; timestamp: number }>;
};
