# scripts/demo_video_shotlist.md — 3-minute backup video shotlist

**Why this exists:** the venue demo can fail for reasons that have nothing to do
with the build — a dead projector, a locked laptop, no time slot. This video is
the fallback that still shows a working system. It is also the safer artefact to
submit, because it is recorded from the same commands anyone can re-run.

**Target: 3:00. Hard ceiling 3:15.** Judges stop watching at three minutes.

**Record with:** any screen recorder at 1920×1080, 30 fps, system audio ON (the
TTS must be audible). Browser at 100% zoom, light theme, bookmarks bar hidden,
notifications off. One continuous take per section; cut between sections.

**Before recording:**

```bash
make up && make seed          # ALL HEALTHY, seed counts printed
make drill                    # must say DRILL PASSED before you record
```

Then **turn the wifi off and leave it off for the entire recording.** The whole
video should be shot offline. That is the point.

---

## Shot list

| # | Time | Duration | On screen | Say this |
|---|---|---|---|---|
| 1 | 0:00 | 0:12 | Title card: *AVSAR — Aspiration-to-Vocational Skilling Assistant & Recommender*, PS ID, team name. Small line bottom-right: **"Recorded with wifi off. No API keys."** | "The PM-AJAY guidelines already require mapping a beneficiary's aspiration to the local job market and an NSQF qualification. Today that happens on paper. This is the voice front door." |
| 2 | 0:12 | 0:10 | The guidelines PDF open at **Ch. 3 §7.A.a.iv**, the clause highlighted | "Chapter 3, paragraph 7.A.a.iv. Aspiration of the target group, and availability of job market. That is the loop we automate." |
| 3 | 0:22 | 0:08 | Terminal: `make up` output ending in **ALL HEALTHY**; then the wifi icon showing disconnected | "Four containers. No keys in the environment. Wifi is off — and stays off." |
| 4 | 0:30 | 0:15 | `http://localhost:3000`, tap **बात शुरू करें**, choose **हिन्दी**, consent screen plays, tap **हाँ** | "Consent first, spoken aloud, recorded before anything is stored. We never ask for a name — the database has no name column." |
| 5 | 0:45 | 0:25 | Five profile screens: district Latur, 18–30, महिला, आठवीं से दसवीं, कोई काम नहीं. Let the four-option layout and the progress bar be visible | "Four options a screen, icon and text, large targets. This is built for someone who cannot read a form." |
| 6 | 1:10 | 0:20 | Mic held; say **"मुझे सिलाई का काम सीखना है"**. Transcript appears, then the read-back confirmation. Tap **हाँ** | "She speaks her aspiration. The system reads back what it heard before it recommends anything — rural ASR error is about one word in four, so we design for it." |
| 7 | 1:30 | 0:25 | Recommendation cards. Zoom on card 1: **AP/Q01868 Self Employed Tailor, NSQF 2.5, seats in Latur**, and the assistance line | "Self Employed Tailor. NSQF level two point five — a half level, which we store as a decimal because 22.9% of NCVET qualifications use them. Forty seats in her own district. And the assistance she can claim: up to ₹50,000 or 50% of project cost, whichever is less." |
| 8 | 1:55 | 0:15 | Split: the SSE `recs` JSON (dev tools) beside the spoken sentence; then terminal running `make grounding` ending in **PASS, 0 ungrounded** | "Every number she just heard came from a database row. The model only wrote the sentence. This check runs 50 random sessions and rejects any digit that is not in the tool output." |
| 9 | 2:10 | 0:25 | `localhost:3000/dashboard`, log in as `officer@demo`. District map/stats, then the **gap panel** | "The officer sees what their district is actually asking for — and the gap panel shows aspirations with no local training supply. That is a procurement decision, not a dashboard." |
| 10 | 2:35 | 0:12 | Click **Export XLSX**, open it, land on **AAP Annexure**, scroll to the **Compliance** sheet | "One click gives the Annual Action Plan annexure, grouped by GIA domain, with a compliance sheet: women participation against the 30% mandate, each figure citing the guideline it comes from." |
| 11 | 2:47 | 0:10 | Terminal: `docker stop avsar-db`, then the PWA showing the spoken Hindi error; `docker start avsar-db` and the app recovering | "Kill the database mid-conversation and she hears a sentence, not a stack trace. It recovers on its own." |
| 12 | 2:57 | 0:03 | Closing card: repo URL, `make up && make seed`, and the line **"Synthetic course data is labelled as synthetic — see docs/ingest-report.md"** | "Everything here runs offline, on committed seeds. Where the government portal was down, our data is synthetic and says so." |

**Total: 3:00.**

---

## The 30-second cut (for a booth loop or a slide embed)

Shots **1 → 6 → 7 → 10**, no narration, captions burned in:

1. 0:00–0:04 title + "wifi off, no API keys"
2. 0:04–0:12 spoken aspiration → transcript → read-back
3. 0:12–0:22 recommendation card with QP code, NSQF 2.5, seats, assistance
4. 0:22–0:30 XLSX export opening on the AAP Annexure sheet

---

## Rules for this recording

- **Do not stage anything.** Every screen is the running system. If a take goes
  wrong, re-record it — do not edit a result in.
- **Do not hide the synthetic-data caveat.** Shot 12 exists for that reason.
  A judge who discovers it themselves reads it as concealment.
- **Do not claim provider latency.** If a shot shows timings, say they are mock
  providers. The keyed Bhashini number has not been measured.
- **Keep the wifi off** for the whole take, and show the disconnected icon at
  least once (shot 3). It is the strongest claim in the video and it costs
  nothing to prove.
- **Audio matters more than video.** If the TTS is inaudible, the voice-first
  claim lands as a screen recording of a form.
