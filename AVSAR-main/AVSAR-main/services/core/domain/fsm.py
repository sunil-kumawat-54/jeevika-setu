"""The beneficiary dialogue state machine — PLAN.md section 4.1.

    [START]
      ├─ LanguageSelect
      ├─ ConsentCapture      (refusal ends the call politely)
      ├─ ProfileCapture      (5 slots: district, age band, gender, education, work)
      ├─ AspirationCapture   (ASR -> parse -> clarify ONCE if low confidence -> confirm)
      ├─ RecommendationBuild (section 6 algorithm)
      ├─ RecommendationSpeak (menu: replay / alternatives / SMS / finish)
      └─ SummaryPersist
    [END]

Rules this module enforces, quoted from the plan:

* *"Every turn <= 2 spoken sentences before yielding."*
* *"If parse confidence < tau: clarify ONCE"* — exactly once; a second
  low-confidence reading proceeds with what was heard rather than looping.
* *"Any ASR empty-result twice -> offer keypad/menu mode automatically."*
* Consent gates everything: no profile slot is persisted before a ``consents``
  row exists (RULE 6 / ARCHITECTURE section 9).

The FSM is a pure function over ``(state, input) -> (state, actions)``. It does
no I/O, which is what lets the whole conversation be unit-tested without a
database, a provider or a network.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

#: Below this ASR confidence the clarify-once branch fires (PLAN.md section 4.1
#: "If parse confidence < tau"). Calibrated against research.md section 5.1's
#: measured ~26.8% WER on rural telephony Hindi: too high and every real
#: utterance triggers a clarification, which field studies show users abandon.
CLARIFY_THRESHOLD = 0.55

#: "Any ASR empty-result twice -> offer keypad/menu mode automatically."
EMPTY_ASR_LIMIT = 2

#: RULE 7 — "Maximum 4 visible options per screen."
MAX_OPTIONS = 4


class Step(str, enum.Enum):
    language_select = "language_select"
    consent = "consent"
    profile_district = "profile_district"
    profile_age_band = "profile_age_band"
    profile_gender = "profile_gender"
    profile_education = "profile_education"
    profile_current_work = "profile_current_work"
    aspiration = "aspiration"
    clarify = "clarify"
    confirm_intent = "confirm_intent"
    recommendation = "recommendation"
    summary = "summary"
    menu_mode = "menu_mode"
    ended = "ended"
    declined = "declined"


#: The five profile slots, in the order PLAN.md section 4.1 asks them.
PROFILE_STEPS: tuple[Step, ...] = (
    Step.profile_district,
    Step.profile_age_band,
    Step.profile_gender,
    Step.profile_education,
    Step.profile_current_work,
)

SLOT_FOR_STEP: dict[Step, str] = {
    Step.profile_district: "district_code",
    Step.profile_age_band: "age_band",
    Step.profile_gender: "gender",
    Step.profile_education: "edu_level",
    Step.profile_current_work: "current_work",
}

#: Steps that count toward the progress indicator (RULE 7: "clear progress
#: indicators"). Consent and language are setup; the summary is the reward.
PROGRESS_STEPS: tuple[Step, ...] = (*PROFILE_STEPS, Step.aspiration, Step.recommendation)


class Action(str, enum.Enum):
    """What the caller must do after a transition. The FSM never does I/O."""

    ask = "ask"
    record_consent = "record_consent"
    persist_slot = "persist_slot"
    build_recommendation = "build_recommendation"
    speak_recommendation = "speak_recommendation"
    replay = "replay"
    speak_alternatives = "speak_alternatives"
    render_summary = "render_summary"
    end_session = "end_session"
    offer_menu_mode = "offer_menu_mode"
    clarify = "clarify"
    handoff_officer = "handoff_officer"


@dataclass
class FsmState:
    """The FSM snapshot persisted in ``sessions.state`` (ARCHITECTURE §4)."""

    step: Step = Step.language_select
    slots: dict[str, Any] = field(default_factory=dict)
    retries: dict[str, int] = field(default_factory=dict)
    empty_asr_streak: int = 0
    clarified: bool = False
    menu_mode: bool = False
    consent_granted: bool = False
    concept: str | None = None
    concept_text: str | None = None
    gia_domain: int | None = None
    turn_no: int = 0
    degraded: bool = False
    officer_callback: bool = False

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "step": self.step.value,
            "slots": dict(self.slots),
            "retries": dict(self.retries),
            "empty_asr_streak": self.empty_asr_streak,
            "clarified": self.clarified,
            "menu_mode": self.menu_mode,
            "consent_granted": self.consent_granted,
            "concept": self.concept,
            "concept_text": self.concept_text,
            "gia_domain": self.gia_domain,
            "turn_no": self.turn_no,
            "degraded": self.degraded,
            "officer_callback": self.officer_callback,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> FsmState:
        payload = payload or {}
        try:
            step = Step(payload.get("step", Step.language_select.value))
        except ValueError:
            step = Step.language_select
        return cls(
            step=step,
            slots=dict(payload.get("slots") or {}),
            retries=dict(payload.get("retries") or {}),
            empty_asr_streak=int(payload.get("empty_asr_streak") or 0),
            clarified=bool(payload.get("clarified")),
            menu_mode=bool(payload.get("menu_mode")),
            consent_granted=bool(payload.get("consent_granted")),
            concept=payload.get("concept"),
            concept_text=payload.get("concept_text"),
            gia_domain=payload.get("gia_domain"),
            turn_no=int(payload.get("turn_no") or 0),
            degraded=bool(payload.get("degraded")),
            officer_callback=bool(payload.get("officer_callback")),
        )

    # -- helpers ----------------------------------------------------------

    @property
    def profile_complete(self) -> bool:
        return all(self.slots.get(SLOT_FOR_STEP[s]) for s in PROFILE_STEPS)

    @property
    def progress(self) -> tuple[int, int]:
        """(current, total) for the progress indicator."""
        total = len(PROGRESS_STEPS)
        if self.step in PROGRESS_STEPS:
            return PROGRESS_STEPS.index(self.step) + 1, total
        if self.step in (Step.summary, Step.ended):
            return total, total
        return 0, total


@dataclass
class Transition:
    state: FsmState
    actions: list[Action] = field(default_factory=list)
    slot: str | None = None
    value: Any = None
    message_key: str | None = None
    error_code: str | None = None

    def has(self, action: Action) -> bool:
        return action in self.actions


@dataclass
class TurnInput:
    """One user input. Exactly one of text/choice/dtmf normally carries meaning."""

    text: str | None = None
    choice: str | None = None
    dtmf: str | None = None
    confidence: float = 1.0
    had_audio: bool = False

    @property
    def value(self) -> str | None:
        for candidate in (self.choice, self.text, self.dtmf):
            if candidate is not None and str(candidate).strip():
                return str(candidate).strip()
        return None

    @property
    def is_empty(self) -> bool:
        return self.value is None


AFFIRMATIVE = {
    "yes", "haan", "ha", "हाँ", "हां", "होय", "అవును", "y", "1", "ok", "sahi", "सही", "बरोबर",
}
NEGATIVE = {"no", "nahi", "नहीं", "नाही", "కాదు", "వద్దు", "n", "2", "0"}


def _is_yes(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.strip().lower()
    return lowered in AFFIRMATIVE or any(token in lowered for token in AFFIRMATIVE)


def _is_no(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.strip().lower()
    return lowered in NEGATIVE or any(token in lowered for token in NEGATIVE)


def next_profile_step(state: FsmState) -> Step:
    """First profile slot still unfilled, else the aspiration step."""
    for step in PROFILE_STEPS:
        if not state.slots.get(SLOT_FOR_STEP[step]):
            return step
    return Step.aspiration


def advance(state: FsmState, turn: TurnInput) -> Transition:
    """Apply one input. Pure — no I/O, no database, no provider."""
    state.turn_no += 1

    # ---- empty ASR handling, before anything step-specific --------------
    # "Any ASR empty-result twice -> offer keypad/menu mode automatically."
    if turn.is_empty and turn.had_audio:
        state.empty_asr_streak += 1
        if state.empty_asr_streak >= EMPTY_ASR_LIMIT and not state.menu_mode:
            state.menu_mode = True
            state.degraded = True
            return Transition(
                state=state,
                actions=[Action.offer_menu_mode, Action.ask],
                message_key="menu_mode",
                error_code="asr_empty",
            )
        return Transition(
            state=state, actions=[Action.ask], message_key=state.step.value, error_code="asr_empty"
        )

    if not turn.is_empty:
        state.empty_asr_streak = 0

    step = state.step

    # ---- language ------------------------------------------------------
    if step == Step.language_select:
        lang = (turn.value or "hi").lower()
        state.slots["lang"] = lang if lang in ("hi", "mr", "te", "en") else "hi"
        state.step = Step.consent
        return Transition(
            state=state, actions=[Action.ask], slot="lang", value=state.slots["lang"],
            message_key=Step.consent.value,
        )

    # ---- consent: the gate before ANY profile slot is stored ------------
    if step == Step.consent:
        if _is_no(turn.value):
            state.step = Step.declined
            return Transition(
                state=state, actions=[Action.end_session], message_key="consent_declined"
            )
        if not _is_yes(turn.value):
            # Not a yes and not a no — ask again rather than assume consent.
            state.retries["consent"] = state.retries.get("consent", 0) + 1
            return Transition(
                state=state, actions=[Action.ask], message_key=Step.consent.value,
                error_code="consent_required",
            )
        state.consent_granted = True
        state.step = next_profile_step(state)
        return Transition(
            state=state,
            actions=[Action.record_consent, Action.ask],
            message_key=state.step.value,
        )

    # ---- profile slots --------------------------------------------------
    if step in PROFILE_STEPS:
        if not state.consent_granted:
            # Defensive: a client must never reach a slot without consent.
            state.step = Step.consent
            return Transition(
                state=state, actions=[Action.ask], message_key=Step.consent.value,
                error_code="consent_required",
            )
        slot = SLOT_FOR_STEP[step]
        state.slots[slot] = turn.value
        state.step = next_profile_step(state)
        return Transition(
            state=state,
            actions=[Action.persist_slot, Action.ask],
            slot=slot,
            value=turn.value,
            message_key=state.step.value,
        )

    # ---- aspiration -----------------------------------------------------
    if step == Step.aspiration:
        state.concept_text = turn.value
        # "If parse confidence < tau: clarify ONCE"
        if turn.confidence < CLARIFY_THRESHOLD and not state.clarified:
            state.clarified = True
            state.step = Step.clarify
            return Transition(
                state=state, actions=[Action.clarify, Action.ask], message_key=Step.clarify.value
            )
        state.step = Step.confirm_intent
        return Transition(
            state=state, actions=[Action.ask], message_key=Step.confirm_intent.value
        )

    if step == Step.clarify:
        # Second reading is accepted whatever its confidence — clarify ONCE.
        state.concept_text = turn.value or state.concept_text
        state.step = Step.confirm_intent
        return Transition(
            state=state, actions=[Action.ask], message_key=Step.confirm_intent.value
        )

    # ---- confirm the parsed intent --------------------------------------
    if step == Step.confirm_intent:
        if _is_no(turn.value):
            # Wrong reading — go back and let them say it again.
            state.step = Step.aspiration
            state.clarified = False
            state.concept = None
            return Transition(
                state=state, actions=[Action.ask], message_key=Step.aspiration.value
            )
        state.step = Step.recommendation
        return Transition(
            state=state,
            actions=[Action.build_recommendation, Action.speak_recommendation],
            message_key=Step.recommendation.value,
        )

    # ---- recommendation menu --------------------------------------------
    if step == Step.recommendation:
        choice = (turn.value or "").lower()
        if choice in ("replay", "1", "फिर सुनें", "पुन्हा ऐका", "మళ్లీ వినండి"):
            return Transition(state=state, actions=[Action.replay], message_key="replay")
        if choice in ("alternatives", "2", "विकल्प सुनें", "पर्याय ऐका", "ఎంపికలు వినండి"):
            return Transition(
                state=state, actions=[Action.speak_alternatives], message_key="alternatives"
            )
        if choice in ("sms", "3", "summary", "sms भेजें"):
            state.step = Step.summary
            return Transition(
                state=state, actions=[Action.render_summary], message_key=Step.summary.value
            )
        if choice in ("officer", "handoff", "callback"):
            state.officer_callback = True
            return Transition(
                state=state, actions=[Action.handoff_officer], message_key="handoff"
            )
        # Anything else (including "finish") closes the loop with a summary.
        state.step = Step.summary
        return Transition(
            state=state, actions=[Action.render_summary], message_key=Step.summary.value
        )

    # ---- summary / terminal ---------------------------------------------
    if step == Step.summary:
        state.step = Step.ended
        return Transition(state=state, actions=[Action.end_session], message_key=Step.ended.value)

    if step == Step.menu_mode:
        # Menu mode re-enters the step it interrupted; the caller restores it.
        state.step = next_profile_step(state) if state.consent_granted else Step.consent
        return Transition(state=state, actions=[Action.ask], message_key=state.step.value)

    return Transition(state=state, actions=[Action.end_session], message_key=Step.ended.value)


def is_terminal(state: FsmState) -> bool:
    return state.step in (Step.ended, Step.declined)
