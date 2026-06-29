"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

function PasswordResetConfirmForm() {
  const params = useSearchParams();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const result = await api.confirmPasswordReset(token, password);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4 py-10">
      <form onSubmit={submit} className="w-full max-w-md rounded-lg border border-black/10 bg-white p-6 shadow-soft">
        <p className="text-sm font-semibold uppercase tracking-wide text-moss">Account recovery</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Choose new password</h1>
        <div className="mt-6 space-y-4">
          <label className="block text-sm font-medium">
            Reset token
            <textarea className="focus-ring mt-1 min-h-24 w-full rounded-lg border border-black/10 px-3 py-2 font-mono text-xs" value={token} onChange={(event) => setToken(event.target.value)} required />
          </label>
          <label className="block text-sm font-medium">
            New password
            <input className="focus-ring mt-1 w-full rounded-lg border border-black/10 px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
          </label>
        </div>
        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {message && <p className="mt-4 rounded-lg bg-mint/50 px-3 py-2 text-sm text-black/70">{message}</p>}
        <button className="focus-ring mt-6 w-full rounded-lg bg-ink px-4 py-3 font-semibold text-white" disabled={loading}>
          {loading ? "Working..." : "Reset password"}
        </button>
        <Link className="mt-4 block text-center text-sm font-semibold text-moss" href="/login">Back to login</Link>
      </form>
    </div>
  );
}

export default function PasswordResetConfirmPage() {
  return (
    <Suspense fallback={<div className="grid min-h-screen place-items-center px-4 py-10 text-ink">Loading...</div>}>
      <PasswordResetConfirmForm />
    </Suspense>
  );
}
