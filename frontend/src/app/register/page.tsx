"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function Register() {
  const [form, setForm] = useState({ email: "", password: "", full_name: "", organization_name: "" });
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const router = useRouter();
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      await api("/auth/register", { method: "POST", body: JSON.stringify(form) });
      const d = await api("/auth/login", { method: "POST", body: JSON.stringify({ email: form.email, password: form.password }) });
      localStorage.setItem("nexora_access", d.access_token);
      localStorage.setItem("nexora_refresh", d.refresh_token);
      router.push("/dashboard");
    } catch (err: any) { setError(err.message); } finally { setBusy(false); }
  }
  const f = (k: string, ph: string, type = "text") => (
    <input className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3" placeholder={ph} type={type}
           value={(form as any)[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} required={k !== "full_name" && k !== "organization_name"} />
  );
  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="text-2xl font-bold">Create your account</h1>
      <form onSubmit={submit} className="mt-6 space-y-4">
        {f("email", "Email", "email")}{f("full_name", "Full name")}
        {f("organization_name", "Business name")}{f("password", "Password (10+ characters)", "password")}
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-indigo-500 py-3 font-semibold disabled:opacity-50">
          {busy ? "Creating..." : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-400">Have an account? <a className="text-indigo-400" href="/login">Sign in</a></p>
    </main>
  );
}
