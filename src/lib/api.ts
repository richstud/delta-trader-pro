import { supabase } from "@/integrations/supabase/client";

const BACKEND_URL =
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? "http://localhost:8010";

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
    ...(await authHeader()),
  };
  const res = await fetch(`${BACKEND_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function openLiveSocket(): Promise<WebSocket> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token ?? "";
  const wsUrl = BACKEND_URL.replace(/^http/, "ws");
  return new WebSocket(`${wsUrl}/ws/live?token=${encodeURIComponent(token)}`);
}

export const BACKEND_BASE = BACKEND_URL;
