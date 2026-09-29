# docs/runbook.md — venue runbook

ARCHITECTURE.md §10 asks for exactly this file:

> Runbook (`docs/runbook.md`): venue checklist (wifi hotspot backup, USB, ngrok
> auth token, volume levels), kill-drill procedure, OTP demo values,
> judge-login accounts.

Everything here has been executed on the build machine. Where a step could not
be verified (anything needing a paid key or a venue), it says so rather than
implying it was tested.

---

## 1. The one thing to remember

**AVSAR needs no internet and no API key to demo.** `VOICE_PROVIDER=mock` and
`LLM_PROVIDER=mock` are the committed defaults. If the venue wifi dies mid-pitch,
nothing happens — there was never a call going out. Say that out loud; it is a
feature, not an excuse.

---

## 2. Pre-venue checklist (do this the night before, on the demo laptop)

| # | Step | Command / check | Expect |
|---|---|---|---|
| 1 | Images built **offline-ready** | `make build` | completes; do this on known-good wifi, it pulls the embedding model |
| 2 | Stack healthy | `make up` | prints `ALL HEALTHY` |
| 3 | Data loaded | `make seed` | prints table counts; idempotent |
| 4 | Backend green | `make test` | exits 0 |
| 5 | Grounding green | `make grounding` | 50/50 sessions grounded, exits 0 |
| 6 | Degradation green | `make drill` | `DRILL PASSED`, 7/7 |
| 7 | Latency sane | `make latency` | all stages within budget |
| 8 | Beneficiary flow by hand | http://localhost:3000 | reach a recommendation in Hindi |
| 9 | Officer flow by hand | http://localhost:3000/dashboard | log in, filter Latur, export CSV |
| 10 | **Turn off wifi and repeat 8 and 9** | — | identical behaviour |
| 11 | Volume | play any TTS turn | audible at arm's length in a noisy hall; test on the laptop's own speakers, not headphones |
| 12 | Screen | 1080p, browser zoom 100%, dark mode off | the dashboard chart legends stay readable on a projector |

**Carry:** the laptop, its charger, a phone with a hotspot (for *uploading* the
deck only, never for the demo), a USB stick with the repo and the exported
`avsar-*.xlsx`, and a printed copy of §5 of this file.

**ngrok:** only needed if a judge wants to open the PWA on their own phone. It
is not part of the scripted demo and requires internet. If you use it, put the
auth token in `.env` as `NGROK_AUTHTOKEN` (it is gitignored) and run
`ngrok http 3000`. Not verified in this build — no account was used.

---

## 3. Accounts and demo values

| What | Value | Source |
|---|---|---|
| Officer login | `officer@demo` / `$DEMO_OFFICER_PASSWORD` (default `avsar-demo-2026`) | `.env`, seeded by `make seed` |
| Viewer login | `viewer@demo` / `$DEMO_VIEWER_PASSWORD` | same |
| Admin login | `admin@demo` / `$DEMO_ADMIN_PASSWORD` | same |
| Beneficiary OTP | **`123456`** for any phone number | `MOCK_OTP` in `.env` |
| Demo districts | Latur (270481) · Nanded (270485) · Varanasi (090187) · Gaya (100196) · Nalgonda (360514) | `seeds/` |

Passwords live in `.env`, never in git (RULE 9). If you change them, re-run
`make seed`.

Roles differ visibly, which is worth showing: viewer sees the dashboard but no
export, officer exports, admin additionally gets the crosswalk console and every
change lands in `audit_log`.

---

## 4. The demo path (rehearse this exact sequence)

1. **http://localhost:3000** → *बात शुरू करें*.
2. Language **हिन्दी**. Consent: play it, then tap **हाँ**. Point out that no
   name is collected — the schema has no name column at all (RULE 6).
3. District **Latur** → age **18 से 30 साल** → gender **महिला** → education **आठवीं से दसवीं**
   → work **कोई काम नहीं**. Four options per screen, big targets (RULE 7).
4. Aspiration: hold the mic and say *"मुझे सिलाई का काम सीखना है"*.
5. Confirm the intent it read back, then let it recommend. Say plainly: the
   course, the NSQF level, the seats and the ₹ figures came from database rows —
   the language model only put them into a sentence, and a numeral guardrail
   rejects any number that is not in the tool JSON (`make grounding` proves it).
6. **http://localhost:3000/dashboard** → log in as `officer@demo` → filter to
   Latur → open the session you just created → show the transcript, the
   recommendation and the consent record → **Export CSV** and **Export XLSX**.
   Open the XLSX: sheet 1 is the AAP annexure, sheet 3 is compliance with
   citations.
7. Show the gap panel: aspirations with no local supply. That is the officer's
   actual procurement signal.
8. If there is time, run the kill drill live (§5).

Synthetic rows are badged in the UI and carry `synthetic=yes` in the export.
Do not skip past that — say which data is real and which is not. It reads as
rigour, and a judge who finds it themselves will read it as the opposite.

---

## 5. Kill-a-service drill (the recovery procedure)

`make drill` runs all three scenarios unattended and exits 0 only if all seven
checks pass. To do it live in front of judges:

**Network off.** Turn off wifi. Complete a full journey. Nothing changes,
because the mock provider is local. (`scripts/drill_offline.py` proves it
harder: it monkeypatches every HTTP transport to raise, and a second pass runs
in `docker run --network none` with no network interface at all.)

**Database down.**
```bash
docker stop avsar-db
curl -i -X POST localhost:8000/sessions -H 'x-avsar-lang: hi' \
     -H 'content-type: application/json' -d '{"channel":"pwa","lang":"hi"}'
```
Expect **HTTP 503** within ~4 s, a `Retry-After` header, and a body whose
`human` field is a speakable Hindi sentence — no stack trace, no driver name.
Recover:
```bash
docker start avsar-db      # /readyz returns to 200 on its own, no restart needed
```

**Provider key revoked.** With real keys configured, a failing provider is tried
twice, demoted, and the mock carries the session; `/readyz` reports
`degraded: true` and the UI badges it. Reproduce without keys:
```bash
make drill     # scenario 3 points the Bhashini adapter at a 401-answering transport
```

**If the whole stack wedges mid-demo:** `make down && make up` (data survives;
the volume is untouched). Only `make clean` deletes data, and then `make seed`
restores it. Never run `make clean` at a venue.

---

## 6. Ops

**Retention.** ARCHITECTURE §11. Dry run first, always:
```bash
make purge                      # 90 days (RETENTION_DAYS), dry run
make purge DAYS=30 APPLY=--apply
```
It deletes sessions, transcripts, recommendations and consents past the cutoff,
keeps `audit_log`, and writes an audit row recording the purge itself. For a
pilot, run it from cron:
```
0 3 * * *  cd /srv/avsar && make purge DAYS=90 APPLY=--apply >> /var/log/avsar-purge.log 2>&1
```

**Rate limits.** `RATE_LIMIT_TURN_PER_MIN` (default 30) and
`RATE_LIMIT_AUTH_PER_MIN` (default 10), Redis-backed with an in-process
fallback so a Redis outage does not lock everyone out. A shared demo laptop
with several judges tapping at once can legitimately hit 30/min — raise it in
`.env` and `make up` again if that happens.

**Latency.** `make latency` drives real journeys and prints p50/p95 per stage
against the ARCHITECTURE §3 budget. It labels mock-mode runs as mock: the
numbers are real measurements of a mock provider, not a Bhashini measurement.

**Logs.** `make logs SVC=core` — structured JSON, one line per event, with
`session_id` on every turn. `/metrics` exposes counters and per-stage p50/p95 in
Prometheus text format.

**Live-check endpoint.** The only code path that may touch a government portal
at runtime is the explicitly labelled live check (RULE 3). It is opt-in, and the
PM-AJAY portal was serving a maintenance page throughout this build — expect it
to fail and say so honestly if a judge asks you to press it.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `make up` hangs at "waiting for services" | first build still pulling the embedding model | wait; `make logs SVC=core` shows progress |
| Dashboard empty | database volume was recreated | `make seed` (idempotent) |
| `429` mid-demo | rate limit, several people tapping at once | wait 60 s, or raise `RATE_LIMIT_TURN_PER_MIN` |
| First turn after boot feels slow | embedder cold start (measured 11.8 s) | `WARM_START=true` (the default) loads it at startup; if you disabled it, re-enable |
| Mic button does nothing | browser blocked the microphone, or the page is not on `localhost`/HTTPS | grant permission; `MediaRecorder` needs a secure context |
| TTS silent | laptop output muted, or the browser tab is muted | check both; the mock always returns audio |
| `make drill` fails on Windows paths | MSYS path translation | the drill already sets `MSYS_NO_PATHCONV=1`; run it from Git Bash, not PowerShell |
| Core 503 on every request | database container stopped | `docker start avsar-db`; recovery is automatic |
