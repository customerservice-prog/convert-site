import type { JobStatusResponse, MetadataResponse } from "../types";

export function getApiBase(): string {
  if (import.meta.env.DEV) return "";
  const { protocol, hostname, port } = window.location;
  if (protocol === "file:") return "http://localhost:8000";
  if (port === "8000" || port === "") return "";
  if (hostname === "localhost" || hostname === "127.0.0.1") return "http://localhost:8000";
  return "";
}

function parseDetail(data: unknown): string {
  if (!data || typeof data !== "object") return "Request failed";
  const d = data as { detail?: unknown };
  const det = d.detail;
  if (det && typeof det === "object" && det !== null && "message" in det) {
    const m = (det as { message?: string }).message;
    if (typeof m === "string") return m;
  }
  if (typeof det === "string") return det;
  return "Request failed";
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const base = getApiBase();
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* ignore */
  }
  if (!res.ok) {
    throw new Error(parseDetail(data));
  }
  return data as T;
}

export function postMetadata(url: string) {
  return apiFetch<MetadataResponse>("/api/info", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function postJob(body: {
  url: string;
  format_id: string;
  output_type: string;
  preset_key?: string | null;
}) {
  return apiFetch<{ job_id: string; status: string; poll_url: string }>("/api/jobs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getJobStatus(jobId: string) {
  return apiFetch<JobStatusResponse>(`/api/jobs/${jobId}`, { method: "GET" });
}
