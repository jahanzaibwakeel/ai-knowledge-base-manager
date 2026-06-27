"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { Archive, ArrowLeft, Download, RefreshCw, RotateCcw } from "lucide-react";
import { Shell } from "@/components/Shell";
import { api, downloadJson } from "@/lib/api";
import { AnalysisJob, DocumentItem, DocumentVersion } from "@/lib/types";

export default function DocumentDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id: routeId } = use(params);
  const [doc, setDoc] = useState<DocumentItem | null>(null);
  const [jobs, setJobs] = useState<AnalysisJob[]>([]);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.document(routeId).then(setDoc).catch((err) => setError(err instanceof Error ? err.message : "Unable to load document"));
    api.analysisJobs(routeId).then(setJobs).catch(() => setJobs([]));
    api.versions(routeId).then(setVersions).catch(() => setVersions([]));
  }, [routeId]);

  async function regenerate() {
    setLoading(true);
    setDoc(await api.regenerate(routeId));
    setJobs(await api.analysisJobs(routeId));
    setLoading(false);
  }

  async function restore(version: number) {
    setLoading(true);
    setDoc(await api.restoreVersion(routeId, version));
    setVersions(await api.versions(routeId));
    setLoading(false);
  }

  async function archiveDocument() {
    setLoading(true);
    await api.archiveDocument(routeId);
    setDoc((current) => current ? { ...current, archived_at: new Date().toISOString() } : current);
    setLoading(false);
  }

  async function restoreArchivedDocument() {
    setLoading(true);
    setDoc(await api.restoreDocument(routeId));
    setLoading(false);
  }

  async function exportDocument() {
    const payload = await api.exportDocument(routeId);
    downloadJson(`document-${routeId}.json`, payload);
  }

  return (
    <Shell>
      <div className="mx-auto max-w-6xl px-4 py-6">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-moss"><ArrowLeft size={16} />Dashboard</Link>
        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {doc && (
          <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.7fr]">
            <section className="rounded-lg border border-black/10 bg-white p-5 shadow-soft">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-moss">{doc.source_type}</p>
                  <h1 className="mt-1 text-3xl font-semibold text-ink">{doc.title}</h1>
                  {doc.filename && <p className="mt-1 text-sm text-black/55">{doc.filename}</p>}
                  {doc.analysis_status !== "complete" && <p className="mt-2 text-sm font-semibold uppercase text-clay">{doc.analysis_status}</p>}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 font-semibold text-white" onClick={regenerate} disabled={loading}>
                    <RefreshCw size={16} />{loading ? "Analyzing" : "Regenerate"}
                  </button>
                  <button className="focus-ring inline-flex items-center gap-2 rounded-lg border border-black/10 px-3 py-2 font-semibold text-ink" onClick={exportDocument} disabled={loading}>
                    <Download size={16} />Export
                  </button>
                  {doc.archived_at ? (
                    <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-moss px-3 py-2 font-semibold text-white" onClick={restoreArchivedDocument} disabled={loading}>
                      <RotateCcw size={16} />Restore
                    </button>
                  ) : (
                    <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-clay px-3 py-2 font-semibold text-white" onClick={archiveDocument} disabled={loading}>
                      <Archive size={16} />Archive
                    </button>
                  )}
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {doc.tags.map((tag) => <span key={tag} className="rounded bg-skyglass px-2 py-1 text-sm">{tag}</span>)}
              </div>
              <h2 className="mt-6 text-lg font-semibold">Original text</h2>
              <article className="mt-3 whitespace-pre-wrap rounded-lg bg-black/[0.03] p-4 leading-7 text-black/75">{doc.content}</article>
            </section>
            <aside className="space-y-4">
              <Panel title="Summary">
                <p className="text-black/70">{doc.summary || "No summary generated yet."}</p>
              </Panel>
              <Panel title="Key points">
                <List items={doc.key_points} empty="No key points yet." />
              </Panel>
              <Panel title="Action items">
                <List items={doc.action_items} empty="No action items yet." />
              </Panel>
              <Panel title="Analysis jobs">
                <List items={jobs.map((job) => `${job.status} ${new Date(job.created_at).toLocaleString()}`)} empty="No jobs yet." />
              </Panel>
              <Panel title="Versions">
                {versions.length === 0 ? (
                  <p className="text-sm text-black/60">No previous versions.</p>
                ) : (
                  <div className="space-y-2">
                    {versions.map((version) => (
                      <button
                        key={version.id}
                        className="focus-ring w-full rounded-lg border border-black/10 px-3 py-2 text-left text-sm hover:bg-skyglass"
                        onClick={() => restore(version.version)}
                        disabled={loading}
                      >
                        v{version.version} {version.reason}
                      </button>
                    ))}
                  </div>
                )}
              </Panel>
            </aside>
          </div>
        )}
      </div>
    </Shell>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-lg border border-black/10 bg-white p-5"><h2 className="text-lg font-semibold text-ink">{title}</h2><div className="mt-3">{children}</div></section>;
}

function List({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) return <p className="text-sm text-black/60">{empty}</p>;
  return <ul className="space-y-2">{items.map((item) => <li key={item} className="rounded-lg bg-mint/50 px-3 py-2 text-sm text-black/75">{item}</li>)}</ul>;
}
