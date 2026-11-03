export default function Home() {
  const features = [
    ["AI Marketing Engine", "Strategy generation, campaign planning, audience and competitor analysis, performance optimization."],
    ["AI Content Studio", "Blogs, SEO articles, social captions, ad copy, emails, hashtags - draft, approve, schedule."],
    ["Autonomous SEO Engine", "Site audits, keyword tracking, technical checks, competitor SEO, clear reports."],
    ["Social Media Automation", "One calendar for Facebook, Instagram, YouTube, LinkedIn, TikTok, Pinterest and X via official APIs."],
    ["AI Voice Agent", "Multilingual conversational agent for support, lead qualification and follow-ups - always labeled as AI."],
    ["Leads, CRM & Sales", "Capture, score, segment and follow up; sales pipeline with approval gates for binding offers."],
    ["Email Marketing", "Compliant campaign builder, segmentation, automation, delivery analytics and unsubscribe handling."],
    ["Website Growth Engine", "Landing pages, blogs, conversion optimization and authorized website integrations."],
  ];
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <p className="text-indigo-400 font-semibold tracking-wide">NEXORA AI</p>
      <h1 className="mt-3 text-4xl md:text-5xl font-bold leading-tight">
        Autonomous AI marketing for every business on earth
      </h1>
      <p className="mt-4 text-lg text-slate-300 max-w-2xl">
        One platform for strategy, content, SEO, social, voice, leads, sales and email. Built on its
        own engine so it runs independently of any single external service.
      </p>
      <div className="mt-8 flex gap-4">
        <a href="/register" className="rounded-lg bg-indigo-500 px-6 py-3 font-semibold hover:bg-indigo-400">Start free</a>
        <a href="/login" className="rounded-lg border border-slate-700 px-6 py-3 font-semibold hover:border-slate-500">Sign in</a>
      </div>
      <div className="mt-16 grid gap-6 md:grid-cols-2">
        {features.map(([t, d]) => (
          <div key={t} className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="font-semibold text-lg">{t}</h2>
            <p className="mt-2 text-slate-400 text-sm">{d}</p>
          </div>
        ))}
      </div>
      <footer className="mt-16 text-sm text-slate-500">© 2026 NEXORA AI. All rights reserved.</footer>
    </main>
  );
}
