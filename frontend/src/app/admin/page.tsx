"use client";
import { useEffect, useState } from "react";
import { api, token } from "@/lib/api";

type Any = Record<string, any>;

export default function Admin() {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState<Any>({});
  const [msg, setMsg] = useState("");
  const [lic, setLic] = useState({ owner_email: "", kind: "commercial", max_activations: 1 });
  const [issuedKey, setIssuedKey] = useState("");

  useEffect(() => { if (!token()) { location.href = "/login"; return; }
    (async () => {
      try {
        const [overview, users, licenses, plans] = await Promise.all([
          api("/admin/overview"), api("/admin/users"), api("/admin/licenses"), api("/admin/plans")]);
        setData({ overview, users, licenses, plans });
      } catch (e: any) { setMsg(e.message); }
    })();
  }, []);

  async function issue(e: React.FormEvent) {
    e.preventDefault(); setMsg("");
    try {
      const d = await api("/admin/licenses/issue", { method: "POST", body: JSON.stringify(lic) });
      setIssuedKey(d.key);
    } catch (e: any) { setMsg(e.message); }
  }

  async function setUserActive(userId: string, active: boolean) {
    try { await api(`/admin/users/${userId}/active`, { method: "PATCH", body: JSON.stringify({ active }) }); location.reload(); }
    catch (e: any) { setMsg(e.message); }
  }

  const tabs: [string, string][] = [["overview", "Overview"], ["users", "Users"], ["licenses", "Licenses"], ["plans", "Plans"]];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Super Admin</h1>
        <button className="text-sm text-slate-400" onClick={() => { localStorage.clear(); location.href = "/login"; }}>Sign out</button>
      </div>
      {msg && <p className="mt-3 text-amber-400 text-sm">{msg}</p>}
      <nav className="mt-6 flex gap-2">
        {tabs.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`rounded-full px-4 py-2 text-sm ${tab === k ? "bg-indigo-500 font-semibold" : "border border-slate-700 text-slate-300"}`}>{label}</button>
        ))}
      </nav>
      {tab === "overview" && (
        <pre className="mt-8 whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-sm">
          {JSON.stringify(data.overview, null, 2)}
        </pre>
      )}
      {tab === "users" && (
        <table className="mt-8 w-full text-sm">
          <thead><tr className="text-left text-slate-400"><th>Email</th><th>Role</th><th>Active</th><th></th></tr></thead>
          <tbody>{(data.users || []).map((u: Any) => (
            <tr key={u.id} className="border-t border-slate-800">
              <td className="py-2">{u.email}</td><td>{u.role}</td><td>{String(u.active)}</td>
              <td><button className="text-indigo-400" onClick={() => setUserActive(u.id, !u.active)}>{u.active ? "Suspend" : "Activate"}</button></td>
            </tr>))}
          </tbody>
        </table>
      )}
      {tab === "licenses" && (
        <div className="mt-8 space-y-6">
          <form onSubmit={issue} className="flex flex-wrap gap-3">
            <input className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2" placeholder="Owner email"
              value={lic.owner_email} onChange={(e) => setLic({ ...lic, owner_email: e.target.value })} required />
            <select className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2" value={lic.kind}
              onChange={(e) => setLic({ ...lic, kind: e.target.value })}>
              {["commercial", "reseller", "trial"].map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
            <input className="w-24 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2" type="number" min={1} max={50}
              value={lic.max_activations} onChange={(e) => setLic({ ...lic, max_activations: Number(e.target.value) })} />
            <button className="rounded-lg bg-indigo-500 px-5 py-2 font-semibold">Issue license</button>
          </form>
          {issuedKey && <p className="text-emerald-400">Issued: <span className="font-mono">{issuedKey}</span></p>}
          <ul className="space-y-2">
            {(data.licenses || []).map((l: Any) => (
              <li key={l.key} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                <span className="font-mono">{l.key}</span> · {l.kind} · {l.status} · {l.bound_domain || "unbound"}
              </li>))}
          </ul>
        </div>
      )}
      {tab === "plans" && (
        <ul className="mt-8 space-y-2">
          {(data.plans || []).map((p: Any) => (
            <li key={p.code} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">{p.code} · ${p.price_monthly}/mo · ${p.price_yearly}/yr</li>))}
        </ul>
      )}
    </main>
  );
}
