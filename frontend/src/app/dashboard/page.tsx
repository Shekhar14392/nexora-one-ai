"use client";
import { useEffect, useState } from "react";
import { api, token } from "@/lib/api";

type Any = Record<string, any>;

export default function Dashboard() {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState<Any>({});
  const [form, setForm] = useState({ kind: "blog", topic: "", language: "English" });
  const [output, setOutput] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => { if (!token()) { location.href = "/login"; return; }
    (async () => {
      try {
        const [analytics, sub, campaigns, leads, content, plans] = await Promise.all([
          api("/marketing/analytics"), api("/billing/subscription"), api("/marketing/campaigns"),
          api("/crm/leads"), api("/marketing/content"), api("/billing/plans")]);
        setData({ analytics, sub, campaigns, leads, content, plans });
      } catch (e: any) { setMsg(e.message); }
    })();
  }, []);

  async function generate(e: React.FormEvent) {
    e.preventDefault(); setMsg(""); setOutput("");
    try {
      const d = await api("/marketing/content/generate", { method: "POST", body: JSON.stringify(form) });
      setOutput(d.body);
    } catch (e: any) { setMsg(e.message); }
  }

  const tabs: [string, string][] = [["overview", "Overview"], ["content", "AI Content Studio"], ["campaigns", "Campaigns"], ["leads", "Leads & CRM"], ["seo", "SEO"], ["billing", "Billing"]];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">NEXORA AI dashboard</h1>
        <button className="text-sm text-slate-400" onClick={() => { localStorage.clear(); location.href = "/login"; }}>Sign out</button>
      </div>
      {msg && <p className="mt-3 text-amber-400 text-sm">{msg}</p>}
      <nav className="mt-6 flex flex-wrap gap-2">
        {tabs.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`rounded-full px-4 py-2 text-sm ${tab === k ? "bg-indigo-500 font-semibold" : "border border-slate-700 text-slate-300"}`}>{label}</button>
        ))}
      </nav>
      {tab === "overview" && (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {[["Campaigns", data.analytics?.campaigns], ["Content items", data.analytics?.content_items],
            ["Leads", data.analytics?.leads], ["Won leads", data.analytics?.won_leads], ["SEO reports", data.analytics?.seo_reports]]
            .map(([label, v]) => (
            <div key={String(label)} className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <p className="text-slate-400 text-sm">{label}</p>
              <p className="mt-1 text-3xl font-bold">{v ?? "..."}</p>
            </div>
          ))}
        </div>
      )}
      {tab === "content" && (
        <div className="mt-8 space-y-4">
          <form onSubmit={generate} className="flex flex-wrap gap-3">
            <select className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2" value={form.kind}
              onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              {["blog", "seo_article", "social_caption", "ad_copy", "product_desc", "email", "hashtags"].map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
            <input className="min-w-[260px] flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2" placeholder="Topic"
              value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} required />
            <input className="w-40 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2" placeholder="Language"
              value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} />
            <button className="rounded-lg bg-indigo-500 px-5 py-2 font-semibold">Generate</button>
          </form>
          {output && <pre className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-sm">{output}</pre>}
        </div>
      )}
      {tab === "campaigns" && (
        <ul className="mt-8 space-y-2">
          {(data.campaigns || []).length === 0 && <p className="text-slate-400">No campaigns yet.</p>}
          {(data.campaigns || []).map((c: Any) => (
            <li key={c.id} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">{c.name} · {c.channel} · {c.status}</li>
          ))}
        </ul>
      )}
      {tab === "leads" && (
        <ul className="mt-8 space-y-2">
          {(data.leads || []).length === 0 && <p className="text-slate-400">No leads yet.</p>}
          {(data.leads || []).map((l: Any) => (
            <li key={l.id} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">{l.name} · {l.email} · score {l.score} · {l.stage}</li>
          ))}
        </ul>
      )}
      {tab === "seo" && <p className="mt-8 text-slate-400">Run audits and keyword tracking from the API (POST /seo/audit) or the admin console. The audit engine is live on the backend.</p>}
      {tab === "billing" && (
        <div className="mt-8">
          <p className="text-slate-300">Current plan: {data.sub?.status === "active" ? data.sub?.plan : "free (no active subscription)"}</p>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {(data.plans || []).map((p: Any) => (
              <div key={p.code} className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                <h3 className="font-semibold">{p.name}</h3>
                <p className="mt-1 text-2xl">${p.price_monthly}/mo</p>
                <p className="mt-2 text-xs text-slate-500">{JSON.stringify(p.limits)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
