'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  BetaNotice,
  ConfidencePill,
  DistrictPicker,
  ErrorBanner,
  MicButton,
  OptionGrid,
  ProgressBar,
  SkipLink,
  SyntheticBadge,
  iconFor,
} from '@/components/ui';
import { TtsPlayer, isRecordingSupported, startRecording } from '@/lib/audio';
import { LANGUAGE_CHOICES, dialogue, errorText, format, menu, ui } from '@/lib/i18n';
import { clearSessionDraft, loadSessionDraft, saveSessionDraft } from '@/lib/offline';
import {
  confirmRecommendation,
  createSession,
  fetchDistricts,
  fetchSummary,
  postTurn,
} from '@/lib/session';
import {
  confidenceBand,
  type ErrorEvent as AvsarError,
  type Lang,
  type Recommendation,
  type SessionState,
  type Summary,
  type TranscriptEvent,
} from '@/lib/types';

type Phase = 'language' | 'conversation' | 'summary';

export default function StartClient() {
  const [phase, setPhase] = useState<Phase>('language');
  const [lang, setLang] = useState<Lang>('hi');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<SessionState | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEvent | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [grounded, setGrounded] = useState<boolean | undefined>();
  const [spoken, setSpoken] = useState<string>('');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<AvsarError | null>(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [micSupported, setMicSupported] = useState(true);
  const [offline, setOffline] = useState(false);

  const player = useRef<TtsPlayer | null>(null);
  const recorder = useRef<Awaited<ReturnType<typeof startRecording>> | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const text = ui(lang);
  const menuText = menu(lang);

  useEffect(() => {
    player.current = new TtsPlayer();
    setMicSupported(isRecordingSupported());
    void loadSessionDraft().then((draft) => {
      if (!draft) return;
      setLang(draft.lang);
      setSessionId(draft.sessionId);
      setState(draft.state);
      setPhase('conversation');
    });
    const online = () => setOffline(!navigator.onLine);
    online();
    window.addEventListener('online', online);
    window.addEventListener('offline', online);
    return () => {
      window.removeEventListener('online', online);
      window.removeEventListener('offline', online);
      player.current?.stop();
    };
  }, []);

  useEffect(() => {
    if (!sessionId || !state || phase !== 'conversation') return;
    void saveSessionDraft({ sessionId, lang, state });
  }, [sessionId, state, lang, phase]);

  // Keep <html lang> in step with the session language. Without this the root
  // stays at the layout's default while the conversation runs in another
  // language, so a screen reader announces Telugu or Marathi content with a
  // Hindi voice (WCAG 3.1.1 Language of Page).
  useEffect(() => {
    if (typeof document !== 'undefined') document.documentElement.lang = lang;
  }, [lang]);

  // Move focus to the new question each turn so a screen-reader user is not
  // stranded at the top of the page (WCAG 2.2 focus management).
  useEffect(() => {
    if (phase === 'conversation' && state) headingRef.current?.focus();
  }, [state?.step, phase]);

  const speak = useCallback((chunkB64: string, mime = 'audio/wav') => {
    player.current?.enqueue(chunkB64, mime);
  }, []);

  const runTurn = useCallback(
    async (payload: Parameters<typeof postTurn>[1]) => {
      if (!sessionId) return;
      setBusy(true);
      setError(null);
      setSpoken('');
      // Barge-in: any new input silences the current reading (ARCHITECTURE §6).
      player.current?.stop();

      const spokenParts: string[] = [];
      await postTurn(sessionId, payload, lang, {
        onTranscript: setTranscript,
        onState: (next) => {
          setState(next);
          if (next.terminal) void loadSummary();
        },
        onRecs: (items, meta) => {
          setRecs(items);
          setGrounded(meta?.grounded);
        },
        onTts: (chunk) => {
          spokenParts.push(chunk.text);
          setSpoken(spokenParts.join(' '));
          speak(chunk.chunk_b64, chunk.mime);
        },
        onError: setError,
      });
      setBusy(false);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sessionId, lang, speak],
  );

  const loadSummary = useCallback(async () => {
    if (!sessionId) return;
    try {
      setSummary(await fetchSummary(sessionId, lang));
      await clearSessionDraft();
      setPhase('summary');
    } catch (err) {
      setError(err as AvsarError);
    }
  }, [sessionId, lang]);

  const begin = async (chosen: Lang) => {
    setLang(chosen);
    setBusy(true);
    setError(null);
    try {
      const created = await createSession(chosen);
      setSessionId(created.session_id);
      setState(created.state);
      setPhase('conversation');
    } catch (err) {
      setError(err as AvsarError);
    } finally {
      setBusy(false);
    }
  };

  const beginRecording = async () => {
    try {
      player.current?.stop();
      recorder.current = await startRecording(() => setRecording(false));
      setRecording(true);
    } catch {
      setMicSupported(false);
      setError({
        code: 'provider_unavailable',
        human: errorText(lang, 'provider_unavailable'),
        retryable: true,
        lang,
      });
    }
  };

  const finishRecording = async () => {
    setRecording(false);
    const handle = recorder.current;
    recorder.current = null;
    if (!handle) return;
    try {
      const audio = await handle.stop();
      await runTurn({ audio_b64: audio });
    } catch {
      setError({ code: 'asr_empty', human: errorText(lang, 'asr_empty'), retryable: true, lang });
    }
  };

  const confirm = async (courseId: number) => {
    if (!sessionId) return;
    setBusy(true);
    try {
      await confirmRecommendation(sessionId, courseId, lang);
      await loadSummary();
    } catch (err) {
      setError(err as AvsarError);
    } finally {
      setBusy(false);
    }
  };

  // ---------------------------------------------------------------- screens

  if (phase === 'language') {
    return (
      <>
        <SkipLink />
        <main id="main" className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-6 p-6">
          <header className="text-center">
            <h1 className="text-4xl font-semibold text-brand-900 dark:text-brand-200">
              {dialogue('hi').steps.language_select.prompt}
            </h1>
            <p className="mt-2 text-lg text-ink-muted">Choose your language</p>
          </header>
          <div className="grid gap-3">
            {LANGUAGE_CHOICES.map((choice) => (
              <button
                key={choice.value}
                type="button"
                disabled={busy}
                onClick={() => begin(choice.value)}
                className="tap-secondary w-full justify-start text-left text-xl"
                lang={choice.value}
              >
                <span aria-hidden="true" className="text-2xl">🗣️</span>
                <span className="flex-1">{choice.label}</span>
                <span className="text-sm text-ink-muted">{choice.english}</span>
              </button>
            ))}
          </div>
          {error && <ErrorBanner message={error.human} />}
        </main>
      </>
    );
  }

  if (phase === 'summary' && summary) {
    const labels = summary.labels ?? {};
    return (
      <>
        <SkipLink />
        <main id="main" className="mx-auto max-w-xl space-y-4 p-6" lang={lang}>
          <h1 className="text-3xl font-semibold text-brand-900 dark:text-brand-200">
            {labels.title ?? 'Summary'}
          </h1>

          <section className="card whitespace-pre-line text-lg leading-indic" aria-label={labels.title}>
            {summary.summary_text}
          </section>

          <div className="flex flex-wrap gap-2">
            {summary.degraded && <span className="chip-warn">⚠ {text.offline_notice}</span>}
            {summary.recommendations.some((r) => r.synthetic) && (
              <SyntheticBadge label={text.synthetic_badge} />
            )}
            {summary.consent_granted && <span className="chip-ok">✓ consent</span>}
          </div>

          <BetaNotice text={text.beta_notice} />

          <div className="grid gap-3">
            <button
              type="button"
              onClick={() => {
                navigator.clipboard?.writeText(summary.summary_text);
              }}
              className="tap-secondary w-full justify-start"
            >
              <span aria-hidden="true">📋</span> <span>{menuText.sms}</span>
            </button>
            <a href="/" className="tap-primary w-full justify-start">
              <span aria-hidden="true">🏠</span> <span>{menuText.finish}</span>
            </a>
          </div>
        </main>
      </>
    );
  }

  if (!state) {
    return (
      <main id="main" className="grid min-h-screen place-items-center p-6">
        <p className="text-lg">{text.processing}</p>
      </main>
    );
  }

  const isProfileStep = state.step.startsWith('profile_');
  const isRecommendation = state.step === 'recommendation';
  const isAspiration = state.step === 'aspiration' || state.step === 'clarify';
  const band = transcript ? confidenceBand(transcript.confidence) : 'high';

  return (
    <>
      <SkipLink />
      <main id="main" className="mx-auto max-w-xl space-y-5 p-6 pb-24" lang={lang}>
        {state.progress.total > 0 && state.progress.current > 0 && (
          <ProgressBar
            current={state.progress.current}
            total={state.progress.total}
            label={format(text.progress, {
              current: state.progress.current,
              total: state.progress.total,
            })}
          />
        )}

        <header>
          <h1
            ref={headingRef}
            tabIndex={-1}
            className="text-2xl font-semibold leading-indic text-ink dark:text-slate-100 focus:outline-none"
          >
            {state.prompt}
          </h1>
          {state.help && <p className="mt-2 text-base text-ink-muted">{state.help}</p>}
        </header>

        {offline && <p className="chip-warn">📴 {text.offline_notice}</p>}
        {state.degraded && <p className="chip-warn">⚠ {text.offline_notice}</p>}

        {/* ---- consent --------------------------------------------------- */}
        {state.step === 'consent' && state.consent && (
          <section className="space-y-4">
            <div className="card space-y-2">
              <p className="text-lg leading-indic">{state.consent.line}</p>
              <p className="text-base text-ink-muted">{state.consent.detail}</p>
              <p className="text-lg font-medium">{state.consent.question}</p>
            </div>
            <div className="grid gap-3">
              <button
                type="button"
                disabled={busy}
                onClick={() => runTurn({ choice: 'yes' })}
                className="tap-primary w-full justify-start"
              >
                <span aria-hidden="true">✅</span> <span>{state.consent.accept}</span>
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => runTurn({ choice: 'no' })}
                className="tap-secondary w-full justify-start"
              >
                <span aria-hidden="true">❌</span> <span>{state.consent.decline}</span>
              </button>
            </div>
          </section>
        )}

        {/* ---- district -------------------------------------------------- */}
        {state.step === 'profile_district' && (
          <DistrictPicker
            disabled={busy}
            placeholder={state.help}
            fetcher={(query) => fetchDistricts(query, lang)}
            onSelect={(code) => runTurn({ choice: code })}
          />
        )}

        {/* ---- other profile slots --------------------------------------- */}
        {isProfileStep && state.step !== 'profile_district' && (
          <OptionGrid
            options={state.options}
            disabled={busy}
            lang={lang}
            moreLabel={menuText.more}
            backLabel={menuText.back}
            onSelect={(value) => runTurn({ choice: value })}
          />
        )}

        {/* ---- aspiration: chips first, free speech second ---------------- */}
        {isAspiration && (
          <section className="space-y-5">
            {state.suggestions && state.suggestions.length > 0 && (
              <div>
                <p className="mb-2 text-base font-medium text-ink-muted">
                  {dialogue(lang).steps.aspiration.help}
                </p>
                <div className="flex flex-wrap gap-2">
                  {state.suggestions.map((suggestion) => (
                    <button
                      key={suggestion.concept}
                      type="button"
                      disabled={busy}
                      onClick={() => runTurn({ text: suggestion.label })}
                      className="tap-secondary text-base"
                    >
                      <span aria-hidden="true">{iconFor(suggestion.icon)}</span>
                      <span>{suggestion.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {micSupported && !state.menu_mode ? (
              <MicButton
                recording={recording}
                busy={busy}
                onStart={beginRecording}
                onStop={finishRecording}
                labels={{
                  speak: text.tap_to_speak,
                  stop: text.tap_to_stop,
                  listening: text.listening,
                  processing: text.processing,
                }}
              />
            ) : (
              <p className="chip-warn">⌨ {dialogue(lang).steps.menu_mode.prompt}</p>
            )}

            {transcript && (
              <ConfidencePill
                text={transcript.text}
                confidence={transcript.confidence}
                band={band}
                labels={{
                  high: text.confidence_high,
                  medium: text.confidence_medium,
                  low: text.confidence_low,
                }}
              />
            )}
          </section>
        )}

        {/* ---- confirm the parsed intent --------------------------------- */}
        {state.step === 'confirm_intent' && (
          <section className="space-y-4">
            {transcript && (
              <ConfidencePill
                text={transcript.text}
                confidence={transcript.confidence}
                band={band}
                labels={{
                  high: text.confidence_high,
                  medium: text.confidence_medium,
                  low: text.confidence_low,
                }}
              />
            )}
            <div className="grid gap-3">
              <button
                type="button"
                disabled={busy}
                onClick={() => runTurn({ choice: 'yes' })}
                className="tap-primary w-full justify-start"
              >
                <span aria-hidden="true">✅</span> <span>{dialogue(lang).options.yes_no[0].label}</span>
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => runTurn({ choice: 'no' })}
                className="tap-secondary w-full justify-start"
              >
                <span aria-hidden="true">🔁</span> <span>{dialogue(lang).options.yes_no[1].label}</span>
              </button>
            </div>
          </section>
        )}

        {/* ---- recommendations ------------------------------------------- */}
        {isRecommendation && recs.length > 0 && (
          <section className="space-y-4" aria-label="recommendations">
            {recs.map((rec) => (
              <article
                key={rec.course_id}
                className={`card space-y-2 ${rec.rank === 1 ? 'border-brand-600 border-2' : ''}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-xl font-semibold leading-indic">{rec.name}</h2>
                  {rec.rank === 1 && <span className="chip-ok">★</span>}
                </div>
                <p className="text-base text-ink-muted">{rec.why}</p>

                <dl className="grid grid-cols-2 gap-2 text-sm">
                  {rec.nsqf_level_spoken !== null && (
                    <div>
                      <dt className="text-ink-muted">{summaryLabel(lang, 'level_label')}</dt>
                      <dd className="font-medium">{rec.nsqf_level_spoken}</dd>
                    </div>
                  )}
                  {rec.hours && (
                    <div>
                      <dt className="text-ink-muted">{summaryLabel(lang, 'duration_label')}</dt>
                      <dd className="font-medium">{rec.hours}</dd>
                    </div>
                  )}
                  {rec.sector && (
                    <div>
                      <dt className="text-ink-muted">{summaryLabel(lang, 'sector_label')}</dt>
                      <dd className="font-medium">{rec.sector}</dd>
                    </div>
                  )}
                  <div>
                    <dt className="text-ink-muted">QP</dt>
                    <dd className="font-mono text-xs">{rec.qp_code}</dd>
                  </div>
                </dl>

                <p className="rounded-lg bg-brand-50 p-3 text-base dark:bg-slate-800">
                  💰 {rec.assistance.loan_support}
                </p>
                {rec.assistance.women_note && (
                  <p className="text-sm text-ok-500">♀ {rec.assistance.women_note}</p>
                )}

                <div className="flex flex-wrap gap-2 pt-1">
                  {rec.synthetic && <SyntheticBadge label={text.synthetic_badge} />}
                  {rec.seats_in_district > 0 && (
                    <span className="chip-ok">🪑 {rec.seats_in_district}</span>
                  )}
                  {rec.stretch && <span className="chip-warn">↗</span>}
                </div>

                <button
                  type="button"
                  disabled={busy}
                  onClick={() => confirm(rec.course_id)}
                  className="tap-primary mt-2 w-full justify-center"
                >
                  <span aria-hidden="true">👍</span> <span>{dialogue(lang).options.yes_no[0].label}</span>
                </button>
              </article>
            ))}

            {grounded !== undefined && (
              <p className="text-xs text-ink-muted">
                {grounded ? '✓ grounded in catalogue data' : '⚠ ungrounded — template fallback used'}
              </p>
            )}

            {/* max 4 options on the menu screen (RULE 7) */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                disabled={busy}
                onClick={() => runTurn({ choice: 'replay' })}
                className="tap-secondary justify-center"
              >
                <span aria-hidden="true">🔁</span> <span>{menuText.replay}</span>
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => runTurn({ choice: 'alternatives' })}
                className="tap-secondary justify-center"
              >
                <span aria-hidden="true">📋</span> <span>{menuText.alternatives}</span>
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => runTurn({ choice: 'sms' })}
                className="tap-secondary justify-center"
              >
                <span aria-hidden="true">✉️</span> <span>{menuText.sms}</span>
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => runTurn({ choice: 'finish' })}
                className="tap-secondary justify-center"
              >
                <span aria-hidden="true">✅</span> <span>{menuText.finish}</span>
              </button>
            </div>
          </section>
        )}

        {spoken && (
          <section className="card" aria-live="polite" aria-label="spoken response">
            <p className="text-base leading-indic text-ink-soft dark:text-slate-300">🔊 {spoken}</p>
          </section>
        )}

        {error && (
          <ErrorBanner
            message={error.human}
            onRetry={error.retryable ? () => runTurn({ choice: 'retry' }) : undefined}
            retryLabel={menuText.replay}
          />
        )}

        <BetaNotice text={text.beta_notice} />
      </main>
    </>
  );
}

function summaryLabel(lang: Lang, key: string): string {
  const labels = dialogue(lang).summary as Record<string, string>;
  return labels[key] ?? key;
}
