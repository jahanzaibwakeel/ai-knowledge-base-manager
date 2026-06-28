"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, ShieldCheck } from "lucide-react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { MetricsStatus, SafetyStatus } from "@/lib/types";

type Probe = {
  health?: string;
  ready?: string;
  safety?: SafetyStatus;
  metrics?: MetricsStatus;
};

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-lg px-3 py-1 text-sm font-semibold ${ok ? "bg-mint text-ink" : "bg-red-50 text-red-700"}`}>
      {ok ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
      {label}
    </span>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4 shadow-soft">
      <p className="text-sm font-medium uppercase text-black/50">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}

export default function SystemPage() {
  const [probe, setProbe] = useState<Probe>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [health, ready, safety, metrics] = await Promise.all([api.health(), api.ready(), api.safety(), api.metrics()]);
      setProbe({ health: health.status, ready: ready.status, safety, metrics });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load system status");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timeout);
  }, []);

  const healthy = probe.health === "ok" && probe.ready === "ready";
  const costSafe = Boolean(probe.safety?.zero_cost_mode && !probe.safety.billing_risk);
  const uptime = useMemo(() => {
    const seconds = probe.metrics?.uptime_seconds ?? 0;
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  }, [probe.metrics?.uptime_seconds]);

  return (
    <Shell>
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase text-moss">Operations</p>
            <h2 className="text-3xl font-semibold text-ink">System status</h2>
          </div>
          <div className="flex gap-2">
            <Link className="focus-ring rounded-lg border border-black/10 bg-white px-4 py-2 font-semibold text-ink" href="/dashboard">
              Dashboard
            </Link>
            <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 font-semibold text-white" onClick={load} disabled={loading}>
              <RefreshCw size={16} /> Refresh
            </button>
          </div>
        </div>

        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <section className="mt-4 rounded-lg border border-black/10 bg-white p-5 shadow-soft">
          <div className="flex flex-wrap gap-2">
            <StatusPill ok={healthy} label={healthy ? "API ready" : "API not ready"} />
            <StatusPill ok={costSafe} label={costSafe ? "Zero-cost safe" : "Billing risk"} />
            <StatusPill ok={!probe.safety?.openai_key_configured} label={probe.safety?.openai_key_configured ? "OpenAI key set" : "No OpenAI key"} />
          </div>
        </section>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Uptime" value={uptime} />
          <MetricCard label="Requests" value={probe.metrics?.total_requests ?? 0} />
          <MetricCard label="In flight" value={probe.metrics?.in_flight ?? 0} />
          <MetricCard label="Avg latency" value={`${probe.metrics?.average_latency_ms ?? 0}ms`} />
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <section className="rounded-lg border border-black/10 bg-white p-5 shadow-soft">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-ink"><ShieldCheck size={18} /> AI safety</h3>
            <dl className="mt-4 grid gap-3 text-sm">
              <div className="flex justify-between gap-4"><dt className="text-black/60">Zero-cost mode</dt><dd className="font-semibold">{String(probe.safety?.zero_cost_mode ?? "")}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-black/60">AI provider</dt><dd className="font-semibold">{probe.safety?.ai_provider ?? "-"}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-black/60">Embedding provider</dt><dd className="font-semibold">{probe.safety?.embedding_provider ?? "-"}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-black/60">Paid AI blocked</dt><dd className="font-semibold">{String(probe.safety?.paid_ai_blocked ?? false)}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-black/60">Paid embeddings blocked</dt><dd className="font-semibold">{String(probe.safety?.paid_embeddings_blocked ?? false)}</dd></div>
            </dl>
          </section>

          <section className="rounded-lg border border-black/10 bg-white p-5 shadow-soft">
            <h3 className="text-lg font-semibold text-ink">Recent server errors</h3>
            <div className="mt-4 space-y-2">
              {probe.metrics?.recent_errors.length ? probe.metrics.recent_errors.map((item, index) => (
                <div key={`${item.path}-${item.timestamp}-${index}`} className="rounded-lg border border-black/10 p-3 text-sm">
                  <p className="font-semibold text-ink">{item.method} {item.path}</p>
                  <p className="text-black/60">{item.status_code} in {item.elapsed_ms}ms</p>
                </div>
              )) : <p className="rounded-lg bg-mint/50 p-3 text-sm text-black/70">No recent 500-level errors.</p>}
            </div>
          </section>
        </div>
      </div>
    </Shell>
  );
}
