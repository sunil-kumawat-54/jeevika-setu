'use client';

import { useEffect, useId, useRef, useState } from 'react';

import type { Option } from '@/lib/types';

/**
 * Accessibility contract for every component here (RULE 7, research.md §9.5):
 *  - at most 4 visible options per screen; longer lists paginate behind "more",
 *    because VideoKheti (CHI 2013) measured that spreading 22 choices over two
 *    screens made selection *harder* than compact sets of ~4;
 *  - tap targets far above the WCAG 2.2 §2.5.8 minimum of 24x24 CSS px;
 *  - icon + text together — icon studies (Kerala, n=58) found concrete icons
 *    help but never replace the label;
 *  - a visible focus ring and full keyboard operation;
 *  - navigation kept linear and shallow (Medhi CHI 2013).
 */

export const MAX_VISIBLE_OPTIONS = 4;

/** Concrete, contextual pictographs. Abstract glyphs test badly with low-literacy users. */
const ICONS: Record<string, string> = {
  child: '🧒', youth: '🧑', adult: '🧔', elder: '🧓',
  female: '👩', male: '👨', other: '🧑',
  none: '🚫', book1: '📗', book2: '📘', book3: '📙', book4: '📕', cap: '🎓',
  search: '🔎', farm: '🌾', craft: '🧵', group: '👭', shop: '🏪',
  check: '✅', cross: '❌',
  tailoring: '🧵', beauty: '💇', electrician: '💡', mobile: '📱',
  dairy: '🥛', poultry: '🐔', food: '🍛', retail: '🏪',
};

export function iconFor(name?: string): string {
  return (name && ICONS[name]) || '•';
}

export function SkipLink() {
  return (
    <a className="skip-link" href="#main">
      मुख्य सामग्री पर जाएँ / Skip to main content
    </a>
  );
}

export function ProgressBar({ current, total, label }: { current: number; total: number; label: string }) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div className="w-full">
      <div className="mb-1.5 flex items-center justify-between text-sm font-medium text-ink-muted dark:text-slate-400">
        <span>{label}</span>
        <span aria-hidden="true">{current}/{total}</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={current}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label={label}
        className="h-3 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
      >
        <div
          className="h-full rounded-full bg-brand-600 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Option grid capped at 4 visible choices. A longer list paginates; nothing is
 * ever hidden without a way to reach it.
 */
export function OptionGrid({
  options,
  onSelect,
  moreLabel = 'और विकल्प',
  backLabel = 'पीछे',
  disabled,
  lang,
}: {
  options: Option[];
  onSelect: (value: string) => void;
  moreLabel?: string;
  backLabel?: string;
  disabled?: boolean;
  lang?: string;
}) {
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [options]);

  const needsPaging = options.length > MAX_VISIBLE_OPTIONS;
  // Reserve one slot for the "more" control so the screen never shows five.
  const perPage = needsPaging ? MAX_VISIBLE_OPTIONS - 1 : MAX_VISIBLE_OPTIONS;
  const pages = needsPaging ? Math.ceil(options.length / perPage) : 1;
  const visible = needsPaging ? options.slice(page * perPage, page * perPage + perPage) : options;

  return (
    <div className="grid gap-3" role="group" aria-label="options">
      {visible.map((option, index) => (
        <button
          key={option.value}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(option.value)}
          className="tap-secondary w-full justify-start text-left"
          lang={lang}
        >
          <span aria-hidden="true" className="text-2xl">{iconFor(option.icon)}</span>
          <span className="flex-1">{option.label}</span>
          <span aria-hidden="true" className="text-sm text-ink-muted">{index + 1}</span>
        </button>
      ))}

      {needsPaging && (
        <button
          type="button"
          disabled={disabled}
          onClick={() => setPage((p) => (p + 1) % pages)}
          className="tap-secondary w-full justify-start text-left"
          aria-label={`${moreLabel} (${page + 1}/${pages})`}
          lang={lang}
        >
          <span aria-hidden="true" className="text-2xl">{page + 1 < pages ? '➡️' : '🔄'}</span>
          <span className="flex-1">{page + 1 < pages ? moreLabel : backLabel}</span>
        </button>
      )}
    </div>
  );
}

/** Live caption with a dot-meter confidence pill (PLAN §7 "confidence UX"). */
export function ConfidencePill({
  text,
  confidence,
  band,
  labels,
}: {
  text: string;
  confidence: number;
  band: 'high' | 'medium' | 'low';
  labels: { high: string; medium: string; low: string };
}) {
  const dots = band === 'high' ? 3 : band === 'medium' ? 2 : 1;
  const tone =
    band === 'high' ? 'chip-ok' : band === 'medium' ? 'chip-warn' : 'chip-danger';
  return (
    <div className="card" aria-live="polite">
      <p className="text-lg leading-indic">{text || '…'}</p>
      <div className="mt-3 flex items-center gap-2">
        <span className={tone}>
          <span aria-hidden="true">
            {'●'.repeat(dots)}
            <span className="opacity-30">{'●'.repeat(3 - dots)}</span>
          </span>
          <span>{labels[band]}</span>
        </span>
        <span className="sr-only">Recognition confidence {Math.round(confidence * 100)} percent</span>
      </div>
    </div>
  );
}

/** Big mic button. Space/Enter operate it; state is announced. */
export function MicButton({
  recording,
  busy,
  onStart,
  onStop,
  labels,
}: {
  recording: boolean;
  busy: boolean;
  onStart: () => void;
  onStop: () => void;
  labels: { speak: string; stop: string; listening: string; processing: string };
}) {
  return (
    <div className="flex flex-col items-center gap-3">
      <button
        type="button"
        onClick={recording ? onStop : onStart}
        disabled={busy}
        aria-pressed={recording}
        className={`flex h-32 w-32 items-center justify-center rounded-full text-5xl shadow-lg transition
          ${recording ? 'bg-danger-500 text-white animate-pulse' : 'bg-brand-700 text-white hover:bg-brand-800'}
          disabled:opacity-50`}
      >
        <span aria-hidden="true">{recording ? '⏹️' : '🎤'}</span>
        <span className="sr-only">{recording ? labels.stop : labels.speak}</span>
      </button>
      <p className="text-lg font-medium" aria-live="polite">
        {busy ? labels.processing : recording ? labels.listening : labels.speak}
      </p>
    </div>
  );
}

/** Speakable error banner — every error must be readable AND sayable (RULE 7). */
export function ErrorBanner({
  message,
  onRetry,
  retryLabel,
  onSpeak,
}: {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  onSpeak?: () => void;
}) {
  if (!message) return null;
  return (
    <div role="alert" className="rounded-xl2 border-2 border-danger-500 bg-danger-100 p-4">
      <p className="text-lg font-medium text-danger-500">{message}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {onSpeak && (
          <button type="button" onClick={onSpeak} className="tap-secondary text-base">
            <span aria-hidden="true">🔊</span> <span>सुनें</span>
          </button>
        )}
        {onRetry && retryLabel && (
          <button type="button" onClick={onRetry} className="tap-primary text-base">
            <span aria-hidden="true">🔁</span> <span>{retryLabel}</span>
          </button>
        )}
      </div>
    </div>
  );
}

/** Honesty badge. Synthetic data is never presented as real government data. */
export function SyntheticBadge({ label }: { label: string }) {
  return (
    <span className="chip-synthetic" title="Synthetic / sample data — not official government data">
      <span aria-hidden="true">⚗️</span>
      <span>{label}</span>
    </span>
  );
}

export function BetaNotice({ text }: { text: string }) {
  return (
    <p className="rounded-lg bg-warn-100 px-3 py-2 text-sm text-warn-500">
      <span aria-hidden="true">⚠️ </span>
      {text}
    </p>
  );
}

/** District type-ahead. Keyboard operable; results announced. */
export function DistrictPicker({
  onSelect,
  fetcher,
  placeholder,
  disabled,
}: {
  onSelect: (code: string, name: string) => void;
  fetcher: (query: string) => Promise<{ code: string; name: string; state: string }[]>;
  placeholder: string;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<{ code: string; name: string; state: string }[]>([]);
  const listId = useId();
  const timer = useRef<number>();

  useEffect(() => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      void fetcher(query).then(setItems);
    }, 180);
    return () => window.clearTimeout(timer.current);
  }, [query, fetcher]);

  return (
    <div>
      <label htmlFor={listId} className="sr-only">
        {placeholder}
      </label>
      <input
        id={listId}
        type="text"
        value={query}
        disabled={disabled}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        className="w-full rounded-xl2 border-2 border-slate-300 px-4 py-4 text-lg
                   focus:border-brand-600 dark:border-slate-700 dark:bg-slate-900"
      />
      <ul className="mt-3 grid gap-2" aria-live="polite">
        {items.slice(0, MAX_VISIBLE_OPTIONS).map((item) => (
          <li key={item.code}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSelect(item.code, item.name)}
              className="tap-secondary w-full justify-start text-left"
            >
              <span aria-hidden="true" className="text-2xl">📍</span>
              <span className="flex-1">
                {item.name}
                <span className="block text-sm text-ink-muted">{item.state}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
