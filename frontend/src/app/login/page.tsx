"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function Login() {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const router = useRouter();
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const d = await login(email, password);
      router.push(d.role === "superadmin" ? "/admin" : "/dashboard");
    } catch (err: any) { setError(err.message); } finally { setBusy(false); }
  }
  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="text-2xl font-bold">Sign in to NEXORA AI</h1>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <input className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3" placeholder="Email"
               type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3" placeholder="Password"
               type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-indigo-500 py-3 font-semibold disabled:opacity-50">
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-400">No account? <a className="text-indigo-400" href="/register">Create one</a></p>
    </main>
  );
}
