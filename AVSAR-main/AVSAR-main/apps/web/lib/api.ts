/**
 * Single egress point from the browser: everything goes to services/core
 * through the BFF route handlers under /api (RULE 8 — the frontend never
 * calls speech providers, LLM providers or government sources directly).
 */
export const CORE_URL =
  process.env.CORE_URL ?? process.env.NEXT_PUBLIC_CORE_URL ?? 'http://localhost:8000';

export type ApiError = {
  code: string;
  retryable: boolean;
  lang: string;
  human: string;
  detail?: string;
};

export async function coreFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = `${CORE_URL}${path}`;
  return fetch(url, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init.headers ?? {}) },
    cache: 'no-store',
  });
}
