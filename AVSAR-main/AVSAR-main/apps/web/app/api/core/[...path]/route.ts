import { NextRequest } from 'next/server';

import { CORE_URL } from '@/lib/api';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

/**
 * BFF proxy to services/core — the single egress point (ARCHITECTURE §1, RULE 8).
 *
 * The browser never holds a speech, LLM or government credential; it only ever
 * talks to this route, which forwards to core server-side. SSE bodies are
 * streamed through untouched so the client can start playing the first TTS
 * chunk while later ones are still being produced.
 */
async function proxy(request: NextRequest, path: string[]) {
  const suffix = path.join('/');
  const search = request.nextUrl.search ?? '';
  const target = `${CORE_URL}/v1/${suffix}${search}`;

  const headers = new Headers();
  for (const key of ['content-type', 'authorization', 'accept', 'x-avsar-lang']) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  // Preserve the caller's address so core's rate limiter buckets per client
  // rather than lumping every browser behind the Next.js server.
  const forwarded = request.headers.get('x-forwarded-for') ?? request.headers.get('x-real-ip');
  if (forwarded) headers.set('x-forwarded-for', forwarded);

  const method = request.method;
  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.text();

  let upstream: Response;
  try {
    upstream = await fetch(target, { method, headers, body, cache: 'no-store' });
  } catch (error) {
    // Core is down (the kill drill does exactly this). Answer with the same
    // speakable error contract core would have used, so the UI can say it aloud
    // instead of showing a dead screen.
    return new Response(
      JSON.stringify({
        detail: {
          code: 'db_unavailable',
          retryable: true,
          lang: 'hi',
          human: 'हमारी जानकारी अभी उपलब्ध नहीं है। थोड़ी देर में फिर कोशिश कीजिए।',
          human_hi: 'हमारी जानकारी अभी उपलब्ध नहीं है। थोड़ी देर में फिर कोशिश कीजिए।',
          detail: String(error),
        },
      }),
      { status: 503, headers: { 'content-type': 'application/json' } },
    );
  }

  const responseHeaders = new Headers();
  for (const key of ['content-type', 'cache-control']) {
    const value = upstream.headers.get(key);
    if (value) responseHeaders.set(key, value);
  }
  // Never buffer an SSE stream.
  responseHeaders.set('X-Accel-Buffering', 'no');

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(request, ctx.params.path);
}

export async function POST(request: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(request, ctx.params.path);
}

export async function PUT(request: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(request, ctx.params.path);
}
