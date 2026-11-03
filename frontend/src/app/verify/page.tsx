"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function VerifyInner() {
  const params = useSearchParams();
  const [state, setState] = useState("Verifying...");
  useEffect(() => {
    const t = params.get("token");
    if (!t) { setState("Missing verification token."); return; }
    api("/auth/verify-email", { method: "POST", body: JSON.stringify({ token: t }) })
      .then(() => setState("Email verified. You can sign in now."))
      .catch((e) => setState(e.message));
  }, [params]);
  return <p className="mt-4 text-slate-300">{state}</p>;
}

export default function Verify() {
  return (
    <main className="mx-auto max-w-md px-6 py-24">
      <h1 className="text-2xl font-bold">Email verification</h1>
      <Suspense><VerifyInner /></Suspense>
    </main>
  );
}
