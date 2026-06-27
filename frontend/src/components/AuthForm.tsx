"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result =
        mode === "login" ? await api.login(email, password) : await api.register(name, email, password);
      setToken(result.access_token);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4 py-10">
      <form onSubmit={submit} className="w-full max-w-md rounded-lg border border-black/10 bg-white p-6 shadow-soft">
        <p className="text-sm font-semibold uppercase tracking-wide text-moss">Knowledge Base Manager</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">{mode === "login" ? "Welcome back" : "Create account"}</h1>
        <div className="mt-6 space-y-4">
          {mode === "register" && (
            <label className="block text-sm font-medium">
              Name
              <input className="focus-ring mt-1 w-full rounded-lg border border-black/10 px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} required />
            </label>
          )}
          <label className="block text-sm font-medium">
            Email
            <input className="focus-ring mt-1 w-full rounded-lg border border-black/10 px-3 py-2" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label className="block text-sm font-medium">
            Password
            <input className="focus-ring mt-1 w-full rounded-lg border border-black/10 px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
          </label>
        </div>
        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <button className="focus-ring mt-6 w-full rounded-lg bg-ink px-4 py-3 font-semibold text-white" disabled={loading}>
          {loading ? "Working..." : mode === "login" ? "Log in" : "Register"}
        </button>
        <p className="mt-4 text-center text-sm text-black/60">
          {mode === "login" ? "No account yet? " : "Already registered? "}
          <Link className="font-semibold text-moss" href={mode === "login" ? "/register" : "/login"}>
            {mode === "login" ? "Register" : "Log in"}
          </Link>
        </p>
      </form>
    </div>
  );
}
