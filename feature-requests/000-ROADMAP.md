# JasonAI Product Roadmap

Vision: a subscription assistant that feels like an **executive assistant, a
creative director, a tech-savvy geek, and a business developer — all in one**.
Target: visionaries, creatives, technologists, out-of-the-box thinkers,
entrepreneurs.

The moat (what makes it winnable): Jason **remembers you** (persistent memory)
and **does things for you** (HQ action bridge + skills). Every feature should
amplify one of those two.

---

## Phase 1 — FOUNDATION ("smooth & stable" — the pre-subscription gate)

Nobody pays for magic that wobbles. Get the ground solid first.

### 1a. Feel-in-control polish (quick wins — do first for momentum)
- **FR-002 — Stop / cancel a message while Jason is working.**
- **FR-003 — Pending / queue composer** (keep typing, line up an addition, see a
  clear "pending" state while Jason works).

### 1b. Trust layer (this is what earns the subscription)
- **Activity / Receipts panel** — a plain log of every real-world action Jason
  took (email sent, task created, event booked). Productizes the "never falsely
  claim done" ethos into something the user can *see*.
- **"Brain" view** — a screen showing what Jason remembers about the user, which
  they can view, correct, and add to. Turns the memory system from a black box
  into a trust-builder. (Grounded in the existing `memory/` system.)

### 1c. Multi-user foundation (the gate to charging anyone)
- **Real accounts** — today the app is single-user (`web/server.py` has one
  email/password). Need multi-user sign-in + **per-user isolated memory**
  (each user gets their own `memory/` + settings, never shared).
- **Sign-in** — BOTH email/password AND "Sign in with Google". (DECIDED Jul 18.)

### 1d. Onboarding
- **A killer first-run** — Jason interviews the new user to seed their memory
  ("tell me about you and what you're working on"), so first impression is
  "it already gets me."

### 1e. Brainpower
- **Model routing / brainpower dial** — today everyone runs on the fast, cheap
  model (Haiku, per `agent/core.py`). Route hard thinking to a stronger model on
  demand; becomes a real difference between tiers.

### 1f. Security & trust (from the 2026-07-18 code review — SECURITY-REVIEW-2026-07-18.md)
The security scan's findings are tracked as FRs and are core to "smooth & stable":
- **FR-004 — Multi-user accounts & per-user isolation** (CRITICAL, = 1c).
- **FR-005 — Sandbox the agent** (CRITICAL; gate to onboarding any 2nd user).
- **FR-006 — Auth hardening** (HIGH; quick wins, do anytime).
- **FR-007 — Rate limiting & usage caps** (HIGH; = the free-tier daily cap).
- **FR-008 — Enforce HQ approval gate in code** (HIGH).
- **FR-009 — Scope history + misc hardening** (MED/LOW).
Rule: do NOT onboard a second real user before FR-004 + FR-005 land.

---

## Phase 2 — DIFFERENTIATION (the sizzle — build once the base is solid)
- **Proactivity** — turn the existing `heartbeat/` engine into morning briefs,
  follow-up radar, and gentle nudges. (No consumer AI feels like it works for you
  in the background; Jason can.)
- **The Four Hats** 👑 — summonable expert modes (Executive Assistant / Creative
  Director / Tech Geek / Business Developer), each swapping tone + the relevant
  skills forward. Extends the Communication-Style toggle (FR-001). The signature
  brand feature.
- **Real project workspaces** — make the sidebar's Projects real containers with
  their own context/memory, so a user runs several ventures without bleed.
- **Jason-managed chats/projects** (FR-00X) — let Jason create/rename/file chats
  and projects on the user's explicit request (consent-gated).

## Phase 3 — PRODUCTIZE
- Billing + tiers, tier enforcement, usage limits.
- **Tiers (DECIDED Jul 18):**
  - **Free — 14-day trial.** Web app only. Daily message limits to cap cost.
  - **Pro.** Includes the desktop version + everything, no daily message cap.
- Polish, marketing site, launch.

---

## Build principle
Do Phase 1 before Phase 2. The magic only sells if the ground under it doesn't
move. Sequence within Phase 1: **1a → 1b → 1c → 1d → 1e**.
