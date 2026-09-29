/** Shapes mirrored from services/core — the BFF is a thin proxy (ARCHITECTURE §1). */

export type Lang = 'hi' | 'mr' | 'te' | 'en';
export const LANGS: Lang[] = ['hi', 'mr', 'te', 'en'];

export type Step =
  | 'language_select'
  | 'consent'
  | 'profile_district'
  | 'profile_age_band'
  | 'profile_gender'
  | 'profile_education'
  | 'profile_current_work'
  | 'aspiration'
  | 'clarify'
  | 'confirm_intent'
  | 'recommendation'
  | 'summary'
  | 'menu_mode'
  | 'ended'
  | 'declined';

export type Option = { value: string; label: string; icon?: string };

export type Suggestion = { concept: string; label: string; icon?: string };

export type ConsentNotice = {
  line: string;
  detail: string;
  question: string;
  accept: string;
  decline: string;
  replay: string;
  granted_ack: string;
  declined_ack: string;
  playback_ref: string;
};

export type SessionState = {
  session_id: string;
  step: Step;
  slots: Record<string, string | null>;
  prompt: string;
  help: string;
  options: Option[];
  options_per_screen: number;
  paginate_options: boolean;
  progress: { current: number; total: number };
  menu_mode: boolean;
  consent_granted: boolean;
  degraded: boolean;
  lang: Lang;
  turn_no: number;
  terminal: boolean;
  officer_callback: boolean;
  consent?: ConsentNotice;
  suggestions?: Suggestion[];
  menu?: Record<string, string>;
};

export type TranscriptEvent = {
  text: string;
  confidence: number;
  provider: string;
  is_final: boolean;
  empty: boolean;
  latency_ms: number;
};

export type Assistance = {
  loan_support: string;
  loan_support_en: string;
  cap_inr: number;
  pct_of_project_cost: number;
  citation?: string;
  women_note?: string;
  women_floor_pct?: number;
};

export type Recommendation = {
  rank: number;
  course_id: number;
  qp_code: string;
  name: string;
  nsqf_level: number | null;
  nsqf_level_spoken: number | null;
  duration_band?: string;
  hours: number | null;
  sector: string | null;
  why: string;
  assistance: Assistance;
  next_step: string;
  score: number;
  seats_in_district: number;
  centres_in_district?: number;
  synthetic: boolean;
  level_inferred?: boolean;
  stretch?: boolean;
  sources?: string[];
  gia_domain_name?: string;
};

export type RecsEvent = {
  items: Recommendation[];
  stretch?: boolean;
  ceiling?: number;
  concept?: string | null;
  grounded?: boolean;
  verbalizer?: string;
  replay?: boolean;
  notes?: string[];
};

export type TtsEvent = {
  index: number;
  text: string;
  chunk_b64: string;
  mime: string;
  provider: string;
  degraded: boolean;
};

export type ErrorEvent = {
  code: string;
  human: string;
  retryable: boolean;
  lang: string;
  refusal?: string;
  detail?: string;
};

export type TurnEvent =
  | { event: 'transcript'; data: TranscriptEvent }
  | { event: 'state'; data: SessionState }
  | { event: 'recs'; data: RecsEvent }
  | { event: 'tts'; data: TtsEvent }
  | { event: 'error'; data: ErrorEvent };

export type Summary = {
  session_id: string;
  lang: Lang;
  summary_text: string;
  labels: Record<string, string>;
  recommendations: Recommendation[];
  confirmed_course_id: number | null;
  district: string | null;
  profile: Record<string, string | null>;
  consent_granted: boolean;
  degraded: boolean;
  synthetic: boolean;
  officer_callback: boolean;
  step: Step;
};

/** Confidence banding for the caption pill (PLAN §7 "confidence UX"). */
export function confidenceBand(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 0.75) return 'high';
  if (confidence >= 0.55) return 'medium';
  return 'low';
}
