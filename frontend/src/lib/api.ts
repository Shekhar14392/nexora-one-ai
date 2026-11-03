export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function token(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("nexora_access");
}

export async function api(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(options.headers as any) };
  const t = token();
  if (t) headers.Authorization = `Bearer ${t}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("nexora_access"); localStorage.removeItem("nexora_refresh");
    if (!location.pathname.startsWith("/login")) location.href = "/login";
  }
  if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail || "Request failed");
  return res.json();
}

export async function login(email: string, password: string) {
  const d = await api("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
  localStorage.setItem("nexora_access", d.access_token);
  localStorage.setItem("nexora_refresh", d.refresh_token);
  return d;
}
