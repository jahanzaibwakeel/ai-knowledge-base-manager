"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

export default function PasswordResetRequestPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setToken("");
    setLoading(true);
    try {
      const result = await api.requestPasswordReset(email);
      setMessage(result.message);
      setToken(result.reset_token ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request reset");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4 py-10">
      <form onSubmit={submit} className="w-full max-w-md rounded-lg border border-black/10 bg-white p-6 shadow-soft">
        <p className="text-sm font-semibold uppercase tracking-wide text-moss">Account recovery</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Reset password</h1>
        <label className="mt-6 block text-sm font-medium">
          Email
          <input className="focus-ring mt-1 w-full rounded-lg border border-black/10 px-3 py-2" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {message && <p className="mt-4 rounded-lg bg-mint/50 px-3 py-2 text-sm text-black/70">{message}</p>}
        {token && (
          <div className="mt-4 rounded-lg border border-black/10 bg-black/[0.03] p-3">
            <p className="text-xs font-semibold uppercase text-black/50">Local reset token</p>
            <p className="mt-2 break-all font-mono text-xs text-ink">{token}</p>
            <Link className="mt-3 inline-block font-semibold text-moss" href={`/password-reset/confirm?token=${encodeURIComponent(token)}`}>
              Continue
            </Link>
          </div>
        )}
        <button className="focus-ring mt-6 w-full rounded-lg bg-ink px-4 py-3 font-semibold text-white" disabled={loading}>
          {loading ? "Working..." : "Create reset token"}
        </button>
        <Link className="mt-4 block text-center text-sm font-semibold text-moss" href="/login">Back to login</Link>
      </form>
    </div>
  );
}
