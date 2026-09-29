'use client';

import type {
  ErrorEvent as AvsarError,
  Lang,
  Recommendation,
  SessionState,
  Summary,
  TranscriptEvent,
  TtsEvent,
} from './types';

const BFF = '/api/core';

export type TurnPayload = {
  text?: string;
  choice?: string;
  dtmf?: string;
  audio_b64?: string;
  variant?: string;
};

export type TurnResult = {
  transcript?: TranscriptEvent;
  state?: SessionState;
  recs?: Recommendation[];
  recsMeta?: { grounded?: boolean; verbalizer?: string; stretch?: boolean; replay?: boolean };
  tts: TtsEvent[];
  errors: AvsarError[];
};

async function parseJsonError(response: Response): Promise<AvsarError> {
  try {
    const body = await response.json();
    const detail = body.detail ?? body;
    return {
      code: detail.code ?? 'network_error',
      human: detail.human ?? detail.human_hi ?? 'Something went wrong.',
      retryable: detail.retryable ?? true,
      lang: detail.lang ?? 'hi',
      detail: detail.detail,
    };
  } catch {
    return {
      code: 'network_error',
      human: 'Something went wrong.',
      retryable: true,
      lang: 'hi',
    };
  }
}

export async function createSession(lang: Lang): Promise<{ session_id: string; state: SessionState }> {
  const response = await fetch(`${BFF}/sessions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-avsar-lang': lang },
    body: JSON.stringify({ channel: 'pwa', lang }),
  });
  if (!response.ok) throw await parseJsonError(response);
  return response.json();
}

/**
 * Post a turn and consume the SSE stream.
 *
 * `onTts` fires per chunk so audio can start on the first sentence while the
 * rest are still arriving (ARCHITECTURE §6 streaming rule).
 */
export async function postTurn(
  sessionId: string,
  payload: TurnPayload,
  lang: Lang,
  handlers: {
    onTranscript?: (event: TranscriptEvent) => void;
    onState?: (state: SessionState) => void;
    onRecs?: (items: Recommendation[], meta: TurnResult['recsMeta']) => void;
    onTts?: (chunk: TtsEvent) => void;
    onError?: (error: AvsarError) => void;
  } = {},
): Promise<TurnResult> {
  const result: TurnResult = { tts: [], errors: [] };

  const response = await fetch(`${BFF}/sessions/${sessionId}/turn`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-avsar-lang': lang },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    const error = await parseJsonError(response);
    result.errors.push(error);
    handlers.onError?.(error);
    return result;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const handleBlock = (block: string) => {
    let name = '';
    const dataLines: string[] = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event: ')) name = line.slice(7).trim();
      else if (line.startsWith('data: ')) dataLines.push(line.slice(6));
    }
    if (!name || dataLines.length === 0) return;
    let data: any;
    try {
      data = JSON.parse(dataLines.join('\n'));
    } catch {
      return;
    }
    switch (name) {
      case 'transcript':
        result.transcript = data;
        handlers.onTranscript?.(data);
        break;
      case 'state':
        result.state = data;
        handlers.onState?.(data);
        break;
      case 'recs':
        result.recs = data.items ?? [];
        result.recsMeta = {
          grounded: data.grounded,
          verbalizer: data.verbalizer,
          stretch: data.stretch,
          replay: data.replay,
        };
        handlers.onRecs?.(result.recs!, result.recsMeta);
        break;
      case 'tts':
        result.tts.push(data);
        handlers.onTts?.(data);
        break;
      case 'error':
        result.errors.push(data);
        handlers.onError?.(data);
        break;
    }
  };

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let split = buffer.indexOf('\n\n');
    while (split !== -1) {
      handleBlock(buffer.slice(0, split));
      buffer = buffer.slice(split + 2);
      split = buffer.indexOf('\n\n');
    }
  }
  if (buffer.trim()) handleBlock(buffer);

  return result;
}

export async function confirmRecommendation(
  sessionId: string,
  courseId: number,
  lang: Lang,
): Promise<{ summary_text: string; summary_lang: Lang }> {
  const response = await fetch(`${BFF}/sessions/${sessionId}/confirm-rec`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-avsar-lang': lang },
    body: JSON.stringify({ course_id: courseId }),
  });
  if (!response.ok) throw await parseJsonError(response);
  return response.json();
}

export async function fetchSummary(sessionId: string, lang: Lang): Promise<Summary> {
  const response = await fetch(`${BFF}/sessions/${sessionId}/summary`, {
    headers: { 'x-avsar-lang': lang },
  });
  if (!response.ok) throw await parseJsonError(response);
  return response.json();
}

export async function fetchDistricts(
  query: string,
  lang: Lang,
): Promise<{ code: string; name: string; state: string }[]> {
  const response = await fetch(
    `${BFF}/districts?q=${encodeURIComponent(query)}&lang=${lang}&limit=8`,
    { headers: { 'x-avsar-lang': lang } },
  );
  if (!response.ok) return [];
  const body = await response.json();
  return body.items ?? [];
}
