"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Filter, RefreshCw } from "lucide-react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { ActivityItem, Paginated, Workspace } from "@/lib/types";

export default function ActivityPage() {
  const [activity, setActivity] = useState<Paginated<ActivityItem>>({ items: [], limit: 50, offset: 0 });
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [workspaceList, activityPage] = await Promise.all([
        api.workspaces(),
        api.activity({ workspace_id: workspaceId, action, entity_type: entityType })
      ]);
      setWorkspaces(workspaceList);
      setActivity(activityPage);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load activity");
    } finally {
      setLoading(false);
    }
  }, [action, entityType, workspaceId]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [load]);

  return (
    <Shell>
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase text-moss">Audit</p>
            <h2 className="text-3xl font-semibold text-ink">Activity timeline</h2>
          </div>
          <div className="flex gap-2">
            <Link className="focus-ring rounded-lg border border-black/10 bg-white px-4 py-2 font-semibold text-ink" href="/dashboard">
              Dashboard
            </Link>
            <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 font-semibold text-white" onClick={() => void load()} disabled={loading}>
              <RefreshCw size={16} /> Refresh
            </button>
          </div>
        </div>

        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <section className="mt-4 rounded-lg border border-black/10 bg-white p-5 shadow-soft">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-ink"><Filter size={18} /> Filters</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <select className="focus-ring rounded-lg border border-black/10 px-3 py-2" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)}>
              <option value="">All workspaces</option>
              {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
            </select>
            <input className="focus-ring rounded-lg border border-black/10 px-3 py-2" placeholder="Action" value={action} onChange={(event) => setAction(event.target.value)} />
            <input className="focus-ring rounded-lg border border-black/10 px-3 py-2" placeholder="Entity type" value={entityType} onChange={(event) => setEntityType(event.target.value)} />
          </div>
        </section>

        <section className="mt-4 rounded-lg border border-black/10 bg-white p-5 shadow-soft">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-semibold text-ink">Recent events</h3>
            <span className="text-sm font-medium text-black/50">{activity.total ?? activity.items.length} events</span>
          </div>
          <div className="mt-4 space-y-3">
            {activity.items.length ? activity.items.map((item) => (
              <article key={item.id} className="rounded-lg border border-black/10 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-lg bg-mint px-2 py-1 text-xs font-bold uppercase text-ink">{item.action}</span>
                    <span className="rounded-lg bg-black/5 px-2 py-1 text-xs font-semibold text-black/60">{item.entity_type}</span>
                  </div>
                  <time className="text-sm text-black/50">{new Date(item.created_at).toLocaleString()}</time>
                </div>
                <p className="mt-3 text-sm text-black/70">{item.message}</p>
              </article>
            )) : <p className="rounded-lg bg-mint/50 p-3 text-sm text-black/70">No activity found for these filters.</p>}
          </div>
        </section>
      </div>
    </Shell>
  );
}
