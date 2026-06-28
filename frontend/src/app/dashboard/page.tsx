"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { FilePlus2, FolderPlus, Library, Plus, Search, Settings, ThumbsDown, ThumbsUp, Upload } from "lucide-react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Dashboard, DocumentItem, RAGAnswer } from "@/lib/types";

function tagsFrom(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<DocumentItem[]>([]);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceDescription, setWorkspaceDescription] = useState("");
  const [collectionName, setCollectionName] = useState("");
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [noteTags, setNoteTags] = useState("");
  const [askQuery, setAskQuery] = useState("");
  const [ragAnswer, setRagAnswer] = useState<RAGAnswer | null>(null);
  const [ragStatus, setRagStatus] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [selectedWorkspace, setSelectedWorkspace] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(preferredWorkspaceId = selectedWorkspace) {
    try {
      const dashboard = await api.dashboard();
      setData(dashboard);
      setSelectedWorkspace(preferredWorkspaceId || dashboard.workspaces[0]?.id || "");
    } catch (err) {
      if (err instanceof Error && err.message.includes("token")) location.href = "/login";
      setError(err instanceof Error ? err.message : "Unable to load dashboard");
    }
  }

  useEffect(() => {
    api.dashboard()
      .then((dashboard) => {
        setData(dashboard);
        setSelectedWorkspace(dashboard.workspaces[0]?.id || "");
      })
      .catch((err) => {
        if (err instanceof Error && err.message.includes("token")) location.href = "/login";
        setError(err instanceof Error ? err.message : "Unable to load dashboard");
      });
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(async () => {
      if (search.trim().length < 2) {
        setResults([]);
        return;
      }
      setResults(await api.search(search));
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [search]);

  const collectionsForWorkspace = useMemo(
    () => data?.collections.filter((collection) => collection.workspace_id === selectedWorkspace) ?? [],
    [data, selectedWorkspace]
  );

  async function createWorkspace(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    await api.createWorkspace(workspaceName, workspaceDescription);
    setWorkspaceName("");
    setWorkspaceDescription("");
    await load();
    setBusy(false);
  }

  async function createCollection(event: FormEvent) {
    event.preventDefault();
    if (!selectedWorkspace) return;
    setBusy(true);
    await api.createCollection(selectedWorkspace, collectionName);
    setCollectionName("");
    await load();
    setBusy(false);
  }

  async function createNote(event: FormEvent) {
    event.preventDefault();
    if (!selectedWorkspace) return;
    setBusy(true);
    await api.createNote({
      workspace_id: selectedWorkspace,
      title: noteTitle,
      content: noteContent,
      tags: tagsFrom(noteTags),
      collection_ids: collectionsForWorkspace.slice(0, 1).map((item) => item.id)
    });
    setNoteTitle("");
    setNoteContent("");
    setNoteTags("");
    await load();
    setBusy(false);
  }

  async function uploadFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedWorkspace) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const tagValue = String(form.get("tags") ?? "");
    form.set("workspace_id", selectedWorkspace);
    form.delete("tags");
    tagsFrom(tagValue).forEach((tag) => form.append("tags", tag));
    setBusy(true);
    await api.uploadDocument(form);
    formElement.reset();
    await load();
    setBusy(false);
  }

  async function askKnowledgeBase(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setRagStatus("retrieving");
    setRagAnswer({ answer: "", citations: [] });
    try {
      const finalAnswer = await api.askStream(askQuery, {
        onStatus: setRagStatus,
        onCitations: (citations) => setRagAnswer((current) => ({ answer: current?.answer ?? "", citations })),
        onToken: (text) => setRagAnswer((current) => ({ answer: `${current?.answer ?? ""}${text}`, citations: current?.citations ?? [] }))
      });
      setRagAnswer(finalAnswer);
      setRagStatus("");
    } finally {
      setBusy(false);
    }
  }

  async function sendFeedback(rating: "helpful" | "not_helpful") {
    if (!ragAnswer?.answer || !askQuery.trim()) return;
    setFeedbackStatus("saving");
    await api.sendRagFeedback({ query: askQuery, answer: ragAnswer.answer, rating, citations: ragAnswer.citations });
    setFeedbackStatus(rating === "helpful" ? "Marked helpful" : "Marked not helpful");
    await load();
  }

  return (
    <Shell>
      <div className="mx-auto max-w-7xl px-4 py-6">
        {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-lg border border-black/10 bg-white p-5 shadow-soft">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-moss">Dashboard</p>
                <h2 className="text-3xl font-semibold text-ink">Your knowledge base</h2>
              </div>
              <select className="focus-ring rounded-lg border border-black/10 px-3 py-2" value={selectedWorkspace} onChange={(event) => setSelectedWorkspace(event.target.value)}>
                {data?.workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
              </select>
            </div>
            {selectedWorkspace && (
              <Link
                className="focus-ring mt-4 inline-flex items-center gap-2 rounded-lg border border-black/10 px-3 py-2 text-sm font-semibold text-ink"
                href={`/workspaces/${selectedWorkspace}/settings`}
              >
                <Settings size={16} />Workspace settings
              </Link>
            )}
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <Stat icon={<Library size={18} />} label="Workspaces" value={data?.workspaces.length ?? 0} />
              <Stat icon={<FolderPlus size={18} />} label="Collections" value={data?.collections.length ?? 0} />
              <Stat icon={<FilePlus2 size={18} />} label="Documents" value={data?.recent_documents.length ?? 0} />
            </div>
            {data?.rag_feedback && data.rag_feedback.total > 0 && (
              <p className="mt-3 rounded-lg bg-skyglass px-3 py-2 text-sm text-black/70">
                RAG feedback: {data.rag_feedback.helpful} helpful, {data.rag_feedback.not_helpful} not helpful
              </p>
            )}
            <label className="mt-5 flex items-center gap-2 rounded-lg border border-black/10 bg-white px-3 py-2">
              <Search size={18} className="text-black/50" />
              <input id="global-search" className="w-full outline-none" placeholder="Search notes, documents, summaries, and tags" value={search} onChange={(event) => setSearch(event.target.value)} />
            </label>
            {results.length > 0 && (
              <div className="mt-3 rounded-lg border border-black/10">
                {results.map((doc) => (
                  <Link key={doc.id} href={`/documents/${doc.id}`} className="block border-b border-black/10 px-4 py-3 last:border-0 hover:bg-mint/40">
                    <p className="font-semibold text-ink">{doc.title}</p>
                    <p className="line-clamp-1 text-sm text-black/60">{doc.summary || doc.content}</p>
                  </Link>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-lg border border-black/10 bg-white p-5 shadow-soft">
            <h2 className="text-xl font-semibold text-ink">AI insights</h2>
            <div className="mt-4 space-y-3">
              {data?.insights.map((insight) => (
                <Link href={`/documents/${insight.document_id}`} key={insight.document_id} className="block rounded-lg border border-black/10 p-3 hover:bg-skyglass">
                  <p className="font-semibold">{insight.title}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-black/65">{insight.summary}</p>
                </Link>
              ))}
              {data?.insights.length === 0 && <p className="text-sm text-black/60">Create or upload a document to generate summaries and action items.</p>}
            </div>
          </section>
        </div>

        <section className="mt-4 rounded-lg border border-black/10 bg-white p-5 shadow-soft">
          <h2 className="text-xl font-semibold text-ink">Ask your knowledge base</h2>
          <form onSubmit={askKnowledgeBase} className="mt-3 flex flex-col gap-3 sm:flex-row">
            <input
              className="focus-ring min-w-0 flex-1 rounded-lg border border-black/10 px-3 py-2"
              placeholder="Ask across notes, uploads, summaries, and indexed chunks"
              value={askQuery}
              onChange={(event) => setAskQuery(event.target.value)}
              minLength={2}
              required
            />
            <button className="focus-ring rounded-lg bg-clay px-4 py-2 font-semibold text-white" disabled={busy}>
              {ragStatus ? "Streaming" : "Ask"}
            </button>
          </form>
          {ragStatus && <p className="mt-3 text-sm font-medium uppercase text-black/50">{ragStatus}</p>}
          {ragAnswer && (
            <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.8fr]">
              <div>
                <p className="min-h-24 rounded-lg bg-mint/50 p-4 leading-7 text-black/75">
                  {ragAnswer.answer || "Preparing answer..."}
                </p>
                {ragAnswer.answer && !ragStatus && (
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button className="focus-ring inline-flex items-center gap-2 rounded-lg border border-black/10 px-3 py-2 text-sm font-semibold text-ink" onClick={() => sendFeedback("helpful")}>
                      <ThumbsUp size={16} />Helpful
                    </button>
                    <button className="focus-ring inline-flex items-center gap-2 rounded-lg border border-black/10 px-3 py-2 text-sm font-semibold text-ink" onClick={() => sendFeedback("not_helpful")}>
                      <ThumbsDown size={16} />Not helpful
                    </button>
                    {feedbackStatus && <span className="text-sm font-medium text-black/55">{feedbackStatus}</span>}
                  </div>
                )}
              </div>
              <div className="space-y-2">
                {ragAnswer.citations.map((citation) => (
                  <Link
                    key={`${citation.document_id}-${citation.chunk_index}`}
                    href={`/documents/${citation.document_id}`}
                    className="block rounded-lg border border-black/10 p-3 hover:bg-skyglass"
                  >
                    <p className="font-semibold text-ink">{citation.document_title}</p>
                    {citation.source_refs?.length ? (
                      <p className="mt-1 text-xs font-medium uppercase text-black/50">
                        {citation.source_refs
                          .slice(0, 3)
                          .map((ref) => ref.label)
                          .filter(Boolean)
                          .join(" | ")}
                      </p>
                    ) : null}
                    <p className="mt-1 line-clamp-2 text-sm text-black/60">{citation.text}</p>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </section>

        <div className="mt-4 grid gap-4 xl:grid-cols-[0.8fr_1.2fr_0.8fr]">
          <section className="rounded-lg border border-black/10 bg-white p-5">
            <h2 className="text-lg font-semibold">Create workspace</h2>
            <form onSubmit={createWorkspace} className="mt-3 space-y-3">
              <input className="focus-ring w-full rounded-lg border border-black/10 px-3 py-2" placeholder="Workspace name" value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} required />
              <textarea className="focus-ring min-h-20 w-full rounded-lg border border-black/10 px-3 py-2" placeholder="Description" value={workspaceDescription} onChange={(event) => setWorkspaceDescription(event.target.value)} />
              <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 font-semibold text-white" disabled={busy}><Plus size={16} />Create</button>
            </form>
            <h2 className="mt-6 text-lg font-semibold">Add collection</h2>
            <form onSubmit={createCollection} className="mt-3 flex gap-2">
              <input className="focus-ring min-w-0 flex-1 rounded-lg border border-black/10 px-3 py-2" placeholder="Collection name" value={collectionName} onChange={(event) => setCollectionName(event.target.value)} required />
              <button className="focus-ring grid h-10 w-10 place-items-center rounded-lg bg-moss text-white" title="Create collection" disabled={busy}><FolderPlus size={18} /></button>
            </form>
          </section>

          <section className="rounded-lg border border-black/10 bg-white p-5">
            <h2 className="text-lg font-semibold">Create note</h2>
            <form onSubmit={createNote} className="mt-3 space-y-3">
              <input className="focus-ring w-full rounded-lg border border-black/10 px-3 py-2" placeholder="Title" value={noteTitle} onChange={(event) => setNoteTitle(event.target.value)} required />
              <textarea className="focus-ring min-h-36 w-full rounded-lg border border-black/10 px-3 py-2" placeholder="Write or paste knowledge here" value={noteContent} onChange={(event) => setNoteContent(event.target.value)} required />
              <input className="focus-ring w-full rounded-lg border border-black/10 px-3 py-2" placeholder="Tags separated by commas" value={noteTags} onChange={(event) => setNoteTags(event.target.value)} />
              <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 font-semibold text-white" disabled={busy}><FilePlus2 size={16} />Save note</button>
            </form>
            <form onSubmit={uploadFile} className="mt-6 rounded-lg bg-mint/50 p-4">
              <h3 className="font-semibold">Upload PDF, TXT, or Markdown</h3>
              <input className="mt-3 w-full text-sm" name="file" type="file" accept=".pdf,.txt,.md,.markdown" required />
              <input className="focus-ring mt-3 w-full rounded-lg border border-black/10 px-3 py-2" name="tags" placeholder="Optional tag" />
              <button className="focus-ring mt-3 inline-flex items-center gap-2 rounded-lg bg-moss px-4 py-2 font-semibold text-white" disabled={busy}><Upload size={16} />Upload</button>
            </form>
          </section>

          <section className="rounded-lg border border-black/10 bg-white p-5">
            <h2 className="text-lg font-semibold">Recent documents</h2>
            <div className="mt-3 space-y-3">
              {data?.recent_documents.map((doc) => (
                <Link href={`/documents/${doc.id}`} key={doc.id} className="block rounded-lg border border-black/10 p-3 hover:bg-mint/40">
                  <p className="font-semibold">{doc.title}</p>
                  {doc.analysis_status !== "complete" && <p className="mt-1 text-xs font-semibold uppercase text-clay">{doc.analysis_status}</p>}
                  <p className="mt-1 line-clamp-2 text-sm text-black/60">{doc.summary || doc.content}</p>
                  <div className="mt-2 flex flex-wrap gap-1">{doc.tags.map((tag) => <span key={tag} className="rounded bg-skyglass px-2 py-1 text-xs">{tag}</span>)}</div>
                </Link>
              ))}
            </div>
            <h2 className="mt-6 text-lg font-semibold">Activity</h2>
            <div className="mt-3 space-y-2">
              {data?.activity.map((item) => <p key={item.id} className="rounded-lg bg-black/[0.03] px-3 py-2 text-sm text-black/70">{item.message}</p>)}
            </div>
          </section>
        </div>
      </div>
    </Shell>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-lg bg-mint/60 p-4">
      <div className="flex items-center gap-2 text-moss">{icon}<span className="text-sm font-medium">{label}</span></div>
      <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
    </div>
  );
}
