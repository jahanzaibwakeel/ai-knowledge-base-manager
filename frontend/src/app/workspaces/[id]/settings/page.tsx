"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ArrowLeft, Crown, Download, Plus, Save, Trash2, Users } from "lucide-react";
import { Shell } from "@/components/Shell";
import { api, downloadJson } from "@/lib/api";
import { DocumentItem, Workspace, WorkspaceMember } from "@/lib/types";

export default function WorkspaceSettings({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [archived, setArchived] = useState<DocumentItem[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState<WorkspaceMember["role"]>("viewer");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([api.workspaces(), api.members(id), api.workspaceDocuments(id, true)])
      .then(([workspaces, memberItems, documents]) => {
        if (!active) return;
        const current = workspaces.find((item) => item.id === id) ?? null;
        setWorkspace(current);
        setName(current?.name ?? "");
        setDescription(current?.description ?? "");
        setMembers(memberItems);
        setArchived(documents.items.filter((doc) => doc.archived_at));
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Unable to load workspace");
      });
    return () => {
      active = false;
    };
  }, [id]);

  async function saveWorkspace() {
    setBusy(true);
    try {
      const updated = await api.updateWorkspace(id, { name, description });
      setWorkspace(updated);
    } finally {
      setBusy(false);
    }
  }

  async function addMember(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.addMember(id, memberEmail, memberRole);
      setMembers(await api.members(id));
      setMemberEmail("");
      setMemberRole("viewer");
    } finally {
      setBusy(false);
    }
  }

  async function updateMemberRole(memberId: string, role: WorkspaceMember["role"]) {
    setBusy(true);
    try {
      await api.updateMember(id, memberId, role);
      setMembers(await api.members(id));
    } finally {
      setBusy(false);
    }
  }

  async function removeMember(memberId: string) {
    setBusy(true);
    try {
      await api.removeMember(id, memberId);
      setMembers(await api.members(id));
    } finally {
      setBusy(false);
    }
  }

  async function transferOwnership(userId: string) {
    setBusy(true);
    try {
      setWorkspace(await api.transferOwnership(id, userId));
      setMembers(await api.members(id));
    } finally {
      setBusy(false);
    }
  }

  async function hardDeleteDocument(documentId: string) {
    setBusy(true);
    try {
      await api.hardDeleteDocument(documentId);
      setArchived((items) => items.filter((item) => item.id !== documentId));
    } finally {
      setBusy(false);
    }
  }

  async function exportWorkspace() {
    const payload = await api.exportWorkspace(id);
    downloadJson(`workspace-${id}.json`, payload);
  }

  return (
    <Shell>
      <div className="mx-auto max-w-6xl px-4 py-6">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-moss"><ArrowLeft size={16} />Dashboard</Link>
        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.8fr]">
          <section className="rounded-lg border border-black/10 bg-white p-5 shadow-soft">
            <p className="text-sm font-semibold uppercase tracking-wide text-moss">Workspace settings</p>
            <h1 className="mt-1 text-3xl font-semibold text-ink">{workspace?.name ?? "Workspace"}</h1>
            <div className="mt-5 space-y-3">
              <input className="focus-ring w-full rounded-lg border border-black/10 px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} />
              <textarea className="focus-ring min-h-24 w-full rounded-lg border border-black/10 px-3 py-2" value={description} onChange={(event) => setDescription(event.target.value)} />
              <div className="flex flex-wrap gap-2">
                <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 font-semibold text-white" onClick={saveWorkspace} disabled={busy}>
                  <Save size={16} />Save
                </button>
                <button className="focus-ring inline-flex items-center gap-2 rounded-lg border border-black/10 px-4 py-2 font-semibold text-ink" onClick={exportWorkspace}>
                  <Download size={16} />Export
                </button>
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-black/10 bg-white p-5 shadow-soft">
            <h2 className="flex items-center gap-2 text-xl font-semibold text-ink"><Users size={20} />Members</h2>
            <form onSubmit={addMember} className="mt-4 space-y-2">
              <input className="focus-ring w-full rounded-lg border border-black/10 px-3 py-2" placeholder="member@example.com" type="email" value={memberEmail} onChange={(event) => setMemberEmail(event.target.value)} required />
              <select className="focus-ring w-full rounded-lg border border-black/10 px-3 py-2" value={memberRole} onChange={(event) => setMemberRole(event.target.value as WorkspaceMember["role"])}>
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
                <option value="owner">Owner</option>
              </select>
              <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-moss px-4 py-2 font-semibold text-white" disabled={busy}><Plus size={16} />Add member</button>
            </form>
            <div className="mt-4 space-y-2">
              {members.map((member) => (
                <div key={member.id} className="rounded-lg bg-black/[0.03] px-3 py-2 text-sm text-black/70">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <p><span className="font-semibold text-ink">{member.name}</span> {member.email}</p>
                    <div className="flex flex-wrap items-center gap-2">
                      {workspace?.owner_id === member.user_id && (
                        <span className="inline-flex items-center gap-1 rounded-lg bg-mint px-2 py-1 text-xs font-bold uppercase text-ink"><Crown size={13} />Owner</span>
                      )}
                      <select className="focus-ring rounded-lg border border-black/10 bg-white px-2 py-1 text-xs font-semibold" value={member.role} onChange={(event) => void updateMemberRole(member.id, event.target.value as WorkspaceMember["role"])} disabled={busy}>
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="owner">Owner</option>
                      </select>
                      <button className="focus-ring rounded-lg border border-black/10 bg-white px-2 py-1 text-xs font-semibold text-ink" onClick={() => void transferOwnership(member.user_id)} disabled={busy || workspace?.owner_id === member.user_id}>
                        Transfer
                      </button>
                      <button className="focus-ring rounded-lg border border-red-200 bg-white px-2 py-1 text-xs font-semibold text-red-700" onClick={() => void removeMember(member.id)} disabled={busy || workspace?.owner_id === member.user_id}>
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="mt-4 rounded-lg border border-black/10 bg-white p-5">
          <h2 className="text-xl font-semibold text-ink">Archived documents</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {archived.map((doc) => (
              <article key={doc.id} className="rounded-lg border border-black/10 p-3">
                <p className="font-semibold text-ink">{doc.title}</p>
                <p className="mt-1 line-clamp-2 text-sm text-black/60">{doc.summary || doc.content}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Link href={`/documents/${doc.id}`} className="focus-ring rounded-lg border border-black/10 px-3 py-1.5 text-sm font-semibold text-ink">
                    View
                  </Link>
                  <button className="focus-ring inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-1.5 text-sm font-semibold text-red-700" onClick={() => void hardDeleteDocument(doc.id)} disabled={busy}>
                    <Trash2 size={15} />Delete forever
                  </button>
                </div>
              </article>
            ))}
            {archived.length === 0 && <p className="text-sm text-black/60">No archived documents.</p>}
          </div>
        </section>
      </div>
    </Shell>
  );
}
