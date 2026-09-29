'use client';

const BFF = '/api/core';
const TOKEN_KEY = 'avsar.officer.token';
const ROLE_KEY = 'avsar.officer.role';

export type Role = 'viewer' | 'officer' | 'admin';

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getRole(): Role | null {
  try {
    return (localStorage.getItem(ROLE_KEY) as Role) ?? null;
  } catch {
    return null;
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
  } catch {
    /* storage can be blocked; the UI just falls back to the login screen */
  }
}

export async function login(email: string, password: string): Promise<{ role: Role }> {
  const response = await fetch(`${BFF}/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.detail?.human ?? 'Sign-in failed');
  }
  try {
    localStorage.setItem(TOKEN_KEY, body.access_token);
    localStorage.setItem(ROLE_KEY, body.role);
  } catch {
    /* ignore */
  }
  return { role: body.role };
}

async function authed<T>(path: string): Promise<T> {
  const token = getToken();
  const response = await fetch(`${BFF}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: 'no-store',
  });
  if (response.status === 401) {
    clearSession();
    throw new Error('unauthorized');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail?.human ?? `Request failed (${response.status})`);
  }
  return response.json();
}

export type Stats = {
  total_sessions: number;
  by_domain: { gia_domain: number; name: string; name_hi: string; count: number }[];
  top_concepts: { concept: string; count: number; gia_domain: number | null }[];
  women_pct: number;
  priority_income_pct: number | null;
  consent_pct: number;
  compliance: Record<string, any>;
  synthetic: { sessions: number; share_pct: number; note?: string };
  can_drill_down: boolean;
};

export type GapItem = {
  concept: string;
  demand_n: number;
  supply_seats: number;
  qp_codes: string[];
  status: 'supplied' | 'no_local_supply' | 'no_qualification';
  flagged: boolean;
};

export type DistrictRow = {
  district_code: string;
  district: string;
  state: string;
  sessions: number;
  women: number;
  women_pct: number;
  meets_women_mandate: boolean;
  consent_pct: number;
  synthetic: number;
};

export type SessionRow = {
  session_id: string;
  district: string | null;
  district_code: string | null;
  lang: string;
  channel: string;
  age_band: string | null;
  gender: string | null;
  edu_level: string | null;
  current_work: string | null;
  consent: boolean;
  degraded: boolean;
  synthetic: boolean;
  officer_callback: boolean;
  created_at: string | null;
};

export type SessionDetail = {
  session_id: string;
  lang: string;
  district: { code: string | null; name: string | null };
  profile: Record<string, unknown>;
  consent: { granted: boolean; records: any[] };
  transcript: {
    turn_no: number;
    provider: string | null;
    text: string | null;
    confidence: number | null;
    parsed_slots: Record<string, unknown> | null;
    latency_ms: number | null;
  }[];
  recommendations: {
    rank: number;
    qp_code: string;
    name: string;
    nsqf_level: number | null;
    sector: string | null;
    score: number;
    factors: Record<string, any>;
    grounded: boolean;
    confirmed: boolean;
    synthetic: boolean;
  }[];
  degraded: boolean;
  synthetic: boolean;
  officer_callback: boolean;
};

export type CrosswalkRow = {
  id: number;
  phrase: string;
  lang: string;
  gia_domain: number;
  gia_domain_name: string;
  concept: string;
  qp_codes: string[];
  status: string;
  version: number;
  is_gap: boolean;
};

const qs = (params: Record<string, string | number | undefined>) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : '';
};

export const fetchStats = (district?: string) =>
  authed<Stats>(`/dashboard/stats${qs({ district })}`);
export const fetchGap = (district?: string) =>
  authed<{ items: GapItem[]; flagged: number; legend: Record<string, string> }>(
    `/dashboard/gap${qs({ district })}`,
  );
export const fetchDistricts = () =>
  authed<{ items: DistrictRow[]; women_mandate_pct: number }>('/dashboard/districts');
export const fetchSessions = (district?: string) =>
  authed<{ total: number; items: SessionRow[] }>(`/dashboard/sessions${qs({ district, limit: 100 })}`);
export const fetchSessionDetail = (id: string) =>
  authed<SessionDetail>(`/dashboard/sessions/${id}`);
export const fetchCrosswalk = (q?: string, gapsOnly?: boolean) =>
  authed<{ total: number; items: CrosswalkRow[]; can_edit: boolean }>(
    `/admin/crosswalk${qs({ q, gaps_only: gapsOnly ? 'true' : undefined, limit: 50 })}`,
  );
export const fetchAuditLog = () =>
  authed<{ items: any[] }>('/admin/audit-log?limit=25');

export async function updateCrosswalk(id: number, patch: Record<string, unknown>) {
  const token = getToken();
  const response = await fetch(`${BFF}/admin/crosswalk/${id}`, {
    method: 'PUT',
    headers: {
      'content-type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(patch),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body?.detail?.human ?? body?.detail?.detail ?? 'Update failed');
  return body;
}

/**
 * Exports need the bearer token, so they cannot be a plain <a href>. Fetch the
 * blob and hand it to the browser as a download.
 */
export async function downloadExport(kind: 'csv' | 'xlsx', district?: string) {
  const token = getToken();
  const path = kind === 'csv' ? '/exports/sessions.csv' : '/exports/aap.xlsx';
  const response = await fetch(`${BFF}${path}${qs({ district })}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error(`Export failed (${response.status})`);
  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') ?? '';
  const match = /filename="([^"]+)"/.exec(disposition);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = match?.[1] ?? `avsar-export.${kind}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  return blob.size;
}
