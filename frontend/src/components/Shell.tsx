"use client";

import Link from "next/link";
import { Activity, BrainCircuit, LogOut, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

export function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  return (
    <main className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-black/10 bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-ink text-white">
              <BrainCircuit size={22} />
            </div>
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-moss">AI Knowledge</p>
              <h1 className="text-lg font-semibold text-ink">Workspace Manager</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              className="focus-ring grid h-10 w-10 place-items-center rounded-lg border border-black/10 bg-white text-ink"
              title="System status"
              href="/system"
            >
              <Activity size={18} />
            </Link>
            <button
              className="focus-ring grid h-10 w-10 place-items-center rounded-lg border border-black/10 bg-white text-ink"
              title="Search"
              onClick={() => document.getElementById("global-search")?.focus()}
            >
              <Search size={18} />
            </button>
            <button
              className="focus-ring grid h-10 w-10 place-items-center rounded-lg border border-black/10 bg-white text-ink"
              title="Log out"
              onClick={() => {
                clearToken();
                router.replace("/login");
              }}
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </header>
      {children}
    </main>
  );
}
