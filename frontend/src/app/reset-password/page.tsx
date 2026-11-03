"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function ResetInner() {
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [state, setState] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setState("");
    try {
      await api("/auth/reset-password", { method: "POST", body: JSON.stringify({ token: params.get("token"), new_password: password }) });
      setState("Password updated. You can sign in now.");
    } catch (e: any) { setState(e.message); }
  }
  return (
    <form onSubmit={submit} className="mt-6 space-y-4">
      <input className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3" type="password" placeholder="New password (10+ characters)"
             value={password} onChange={(e) => setPassword(e.target.value)} required minLength={10} />
      {state && <p className="text-sm text-slate-300">{state}</p>}
      <button className="w-full rounded-lg bg-indigo-500 py-3 font-semibold">Update password</button>
    </form>
  );
}

export default function ResetPassword() {
  return (
    <main className="mx-auto max-w-md px-6 py-24">
      <h1 className="text-2xl font-bold">Set a new password</h1>
      <Suspense><ResetInner /></Suspense>
    </main>
  );
}
