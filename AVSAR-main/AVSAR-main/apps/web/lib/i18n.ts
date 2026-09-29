import type { Lang } from './types';

import en from '@prompts/dialogue.en.json';
import hi from '@prompts/dialogue.hi.json';
import mr from '@prompts/dialogue.mr.json';
import te from '@prompts/dialogue.te.json';

/**
 * i18n comes straight from `data/prompts/dialogue.{lang}.json` — the same files
 * the server speaks from (PLAN §5.2: "every spoken prompt as data (not
 * hardcoded strings) so language QA is parallelizable"). Importing them rather
 * than re-typing the strings keeps screen text and spoken text in lockstep.
 */
export const DIALOGUE = { hi, mr, te, en } as const;

export type Dialogue = typeof hi;

export function dialogue(lang: Lang): Dialogue {
  return (DIALOGUE[lang] ?? DIALOGUE.hi) as Dialogue;
}

export function ui(lang: Lang) {
  return dialogue(lang).ui;
}

export function menu(lang: Lang) {
  return dialogue(lang).menu;
}

export function summaryLabels(lang: Lang) {
  return dialogue(lang).summary;
}

export function errorText(lang: Lang, code: string): string {
  const errors = dialogue(lang).errors as Record<string, string>;
  return errors[code] ?? errors.network_error ?? '';
}

export const LANGUAGE_CHOICES: { value: Lang; label: string; english: string }[] = [
  { value: 'hi', label: 'हिंदी', english: 'Hindi' },
  { value: 'mr', label: 'मराठी', english: 'Marathi' },
  { value: 'te', label: 'తెలుగు', english: 'Telugu' },
  { value: 'en', label: 'English', english: 'English' },
];

export function format(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_match, key) =>
    values[key] === undefined ? `{${key}}` : String(values[key]),
  );
}
