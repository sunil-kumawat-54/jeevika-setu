import { del, get, set } from 'idb-keyval';

import type { Lang, SessionState } from './types';

const DRAFT_KEY = 'avsar.active-session';

export type SessionDraft = {
  sessionId: string;
  lang: Lang;
  state: SessionState;
  savedAt: number;
};

export async function saveSessionDraft(draft: Omit<SessionDraft, 'savedAt'>) {
  await set(DRAFT_KEY, { ...draft, savedAt: Date.now() } satisfies SessionDraft);
}

export async function loadSessionDraft(): Promise<SessionDraft | undefined> {
  const draft = await get<SessionDraft>(DRAFT_KEY);
  if (!draft || Date.now() - draft.savedAt > 24 * 60 * 60 * 1000) {
    if (draft) await del(DRAFT_KEY);
    return undefined;
  }
  return draft;
}

export async function clearSessionDraft() {
  await del(DRAFT_KEY);
}