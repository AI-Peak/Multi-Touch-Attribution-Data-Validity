# Frontend Design Brief — MTA Data Validity Dashboard

A self-contained prompt for the agent that will design and build the Next.js frontend
for this project. Read this top-to-bottom **before** touching code.

---

## 1. What this project is (and isn't)

This is the companion web app for a **methodology-caution research paper**, not a
marketing analytics dashboard. The whole intellectual point is the opposite of what
a typical attribution dashboard claims:

> The public Multi-Touch Attribution dataset (10,000 touchpoints, 2,847 users)
> has a **conversion-label validity problem**. It should not be used for direct
> channel-winner claims or causal budget reallocation. This app shows the audit
> evidence and provides a defensible workflow instead.

Three research questions structure every page:

- **RQ1** — Is the dataset valid enough for direct multi-touch attribution?
- **RQ2** — What evidence shows label bias, weak channel signal, or confounding?
- **RQ3** — Given the limitations, what analysis strategy is safer?

The headline finding is the **83.63% user any-Yes conversion rate** (≈ 28× a 3%
e-commerce benchmark) and the **channel AUC of 0.4902** (indistinguishable from
chance). Channel "performance" is largely a journey-length artefact.

Every design decision should respect this framing. **No causal claims, no
"winner" framing, no marketing tone.** Amber warnings carry the paper's
intellectual honesty — they are not decorative.

---

## 2. Stack (committed)

| Layer | Choice | Notes |
|---|---|---|
| Framework | **Next.js 15 (App Router)** | Server Components for shell, client islands for interactive bits |
| Language | **TypeScript strict** | `noUncheckedIndexedAccess: true` |
| Styling | **Tailwind CSS v4** + CSS variables | Tokens defined as CSS vars so Tailwind utilities and raw CSS stay in sync |
| Charts | **Recharts** | Theme it; no Plotly, no D3-from-scratch |
| Icons | **Lucide React** | Pair with existing 24×24 stroke style from `script JS/data.jsx` |
| Fonts | `next/font/google` for IBM Plex Sans + IBM Plex Mono + **one editorial display face** (see §6) | Subset, preload, swap=auto |
| AI | `@google/genai` SDK, called from a **Next.js Route Handler** (`app/api/chat/route.ts`) | API key NEVER reaches the browser |
| Runtime / pkg mgr | Node ≥ 20, **pnpm** | Lockfile committed |
| Lint / format | ESLint (`next/core-web-vitals`) + Prettier | Configured but not bikeshed |
| State | React `useState` + URL search params for shareable simulator state | No Redux, no Zustand unless you genuinely need it |

If a library choice above feels wrong for a specific page, push back in your
plan **before** implementing — don't silently swap.

---

## 3. Repo placement

The Next.js project **replaces** the current `app/` contents (which is a JSX
prototype scaffold, already served its purpose as a design exploration).

```
Multi-Touch-Attribution-Data-Validity/
├── analysis_python/        ← UNTOUCHED
├── analysis_sql/           ← UNTOUCHED
├── data/                   ← UNTOUCHED
├── model/                  ← UNTOUCHED
├── scripts/                ← UNTOUCHED (pipeline)
├── outputs/                ← read-only source for figure PNGs if needed
└── app/                    ← Next.js project root lives HERE
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── postcss.config.mjs
    ├── src/
    │   ├── app/            ← Next.js App Router
    │   ├── components/
    │   ├── lib/
    │   └── styles/
    ├── data/generated/     ← KEEP — five JSON files consumed at build time
    ├── mockup-screenshots/ ← reference images (copy from external archive)
    ├── public/             ← figure PNGs, favicon
    └── scripts/prepare_app_data.py  ← KEEP (pipeline-owned)
```

**Before starting:** delete the existing `app/script JS/` folder and the
`app/README.md` (scaffold-only). Preserve `app/data/generated/` and
`app/scripts/prepare_app_data.py`.

**Do NOT touch:** `data/`, `analysis_sql/`, `analysis_python/`, `model/`,
`scripts/` (root), `outputs/`. Those belong to the reproducible pipeline.

---

## 4. Data contract — `app/data/generated/*.json`

The pipeline writes five JSON files into `app/data/generated/`. The frontend
reads **only these files** — never raw CSV, never the SQL outputs.

| File | Shape (top-level keys) | Used by |
|---|---|---|
| `audit-data.json` | `sql_baseline.{conversion_rates, label_event_audit, ...}`, `python_analysis.{...}` | Overview, RQ1 |
| `attribution-data.json` | `sql_baseline.attribution_baseline[]` (per label_scenario × channel: first/last/linear %) | Overview, RQ3 |
| `model-data.json` | `logistic_regression.metrics[]`, `markov.{...}` | Overview, RQ2 |
| `sensitivity-data.json` | `rank_stability[]` (per scenario: spearman vs current, top channel, share) | Overview, RQ3 |
| `simulation-data.json` | `simulation_results[]` (per S0..Sn: conversions, revenue, deltas) | RQ3 simulator |

**Important data hygiene:**

- `sensitivity-data.json` contains literal `NaN` tokens — they're invalid JSON.
  Either fix in `prepare_app_data.py` (write `null`) or pre-process in a
  build step. Don't paper over with try/catch.
- Treat all numbers as `number | null`. Display `—` for nulls, never `NaN`
  or `undefined` in UI.
- Schema-validate at load time with **Zod**. A failed validation should fail
  the build, not crash at runtime.

**Loading strategy:**

- Default to **static import** in Server Components:
  `import auditData from '@/data/generated/audit-data.json'`. Next.js will
  inline at build time; zero runtime fetch.
- For pages that need fresh data on every build but not at request time,
  this works. We are not running a backend.
- The interactive simulator (RQ3) is fully client-side math on already-loaded
  JSON — no API calls.

---

## 5. The six pages

Mockup screenshots (six PNGs, one per page) are the **visual source of truth**
for layout and information hierarchy. They live in `app/mockup-screenshots/`
once you copy them from the external prompts archive at
`F:\Sem 4\DAP391\MTA-Data validate\app\mockup-screenshots\`.

The existing `app/script JS/pages-a.jsx` and `pages-b.jsx` are the **content
source of truth** — they encode the exact text, the exact KPI labels, the
exact tab structures, the chart compositions. Port them faithfully, then
refine visually (see §6).

### Sidebar (always visible)

- Dark navy (`#1a2734`) background, fixed 240px width
- Brand block at top: `MTA` glyph + "Data Validity Dashboard" / "Multi-Touch Attribution" tagline
- Section label `RESEARCH VIEWS` (uppercase, micro caps, 10px)
- Six nav items with monospace index `01–06`, label, optional `beta` tag
- Active state: subtle navy lift + white text + accented index chip
- Footer: **Data status** panel — 4×4 grid of K/V pairs (Files loaded, Touchpoints, Last refresh, Pipeline version) with a small "ok" status dot

### Persistent validity banner (always visible, above scroll area)

Amber tint band:
> **Validity-audit & scenario-exploration tool.** This dashboard does not provide causal budget optimization.

### Page 1 — Overview

- Eyebrow: `OVERVIEW · DATA VALIDITY AUDIT`
- H1: `Dataset validity at a glance`
- Subtitle: 1-line context about what the metrics show
- 6 KPI cards in a single row (last is warning-styled: "Main conclusion — Not safe for direct attribution")
- "Diagnostic panels" 2×2 grid: Conversion rate gap (bar), Label-event audit (hbar), Model comparison (bar), Sensitivity stability (bar). Each card carries a small `RQ1` / `RQ2` / `RQ3` tag in its footer.
- Footnote: "All panels derive from the same precomputed pipeline. Charts are diagnostic, not prescriptive."

### Page 2 — RQ1 Validity Audit

- Eyebrow: `RQ1 · VALIDITY AUDIT`
- H1: `Is the dataset valid enough for direct multi-touch attribution?`
- **Interactive slider**: "Expected e-commerce conversion benchmark (%)" range 1–10, step 0.5, default 3
- 3 computed result cards: Observed user any-Yes (83.63%, fixed), Selected benchmark (slider value), **Gap multiplier** (warning style, shows ×, with a saturation chip Low/Medium/High based on gap)
- Evidence table: 4 rows of label-validity checks with `Concern` chip column
- Conclusion callout (amber): "Conclusion — RQ1" with dynamic text using current slider value

### Page 3 — RQ2 Model Diagnostics

- Eyebrow: `RQ2 · MODEL DIAGNOSTICS`
- H1: `What evidence shows label bias, weak channel signal, or confounding?`
- "View controls" card with 2 dropdowns (Metric, Diagnostic view)
- 4 tabs: **Channel signal test** / **Logistic regression comparison** / **Journey-length confounding** / **Markov removal effect**
- Each tab: 2-column layout — chart on left, metrics table on right
- Interpretation callout (neutral/info style, not warning): "Interpretation — RQ2"

### Page 4 — RQ3 Interactive Simulator

The most interactive page. Two-column layout (380px input panel + 1fr output panel).

**Inputs panel:**
- Total marketing budget (number input, $ prefix, default 100000)
- Revenue per conversion (number input, $ prefix, default 100)
- Conversion label scenario (select, 6 options)
- Attribution method (select, 6 options)
- Allocation mode (radio: Auto from method / Manual sliders)
- If Manual: 6 channel sliders that auto-normalize to 100%

**Outputs panel:**
- Budget allocation table with Stability badge (Stable / Moderate / Unstable) in the header
- 2×2 stat grid: Estimated conversions (dark navy accent card, white text), Estimated revenue, Δ conv vs equal split, Δ revenue vs equal split
- Warning callout: "What-if diagnostic — not a recommendation"

**State**: persist all input values in URL search params (`?budget=100000&method=Markov&...`) for shareability.

### Page 5 — AI Research Assistant ("Ask the evidence")

- Eyebrow: `AI RESEARCH ASSISTANT`
- H1: `Ask the evidence` (sidebar still says "AI Assistant")
- Subtitle + neutral info banner: "Powered by Gemini. Answers grounded in project evidence only. May make mistakes."
- Initial assistant greeting card
- Chat thread: user bubbles right-aligned navy, assistant bubbles left-aligned white-bordered
- 5 Vietnamese prompt chips above the input
- Input bar pinned at bottom: textarea + send button (navy square)

**Backend**: `app/api/chat/route.ts` Edge route. Streams Gemini response.
System instruction + compact evidence summary are baked in server-side (see §7).
Vietnamese-by-default unless user asks for English. Refuses causal-channel-winner framing.

### Page 6 — Safe Recommendation

- Eyebrow: `SAFE RECOMMENDATION`
- H1: `Given the limitations, the safer path forward`
- "Recommended analysis workflow" — 5-step flow + 1 OUTPUT card (terminal/warning-styled), with arrow separators
- Two-column section below: green "Safer analysis strategies" check-list (4 items) + amber "Do NOT" cross-list (3 items)
- Bottom callout (neutral/info style): "Bottom line" with the key takeaway

---

## 6. Aesthetic direction — "Refined academic working-paper"

The existing JSX prototype establishes the spine of the design language. **Port
its restraint and precision faithfully, then elevate three specific things**:
typography hierarchy, one signature interaction, and material texture.

### 6.1 Tokens to PORT verbatim from `app/script JS/styles.css`

```
--paper:       #f4f3ef    /* page background — warm off-white */
--surface:     #ffffff
--surface-2:   #faf9f6
--surface-sunk:#f0efea
--line:        #e3e1da
--line-strong: #cfccc2

--ink:         #20262e    /* primary text */
--ink-2:       #4a525c    /* secondary */
--ink-3:       #79808a    /* tertiary */
--ink-faint:   #a3a8b0    /* footnotes */

--navy:        #1e3a5f    /* primary accent */
--navy-600:    #274a76
--navy-300:    #6f86a3
--navy-tint:   #eaeef4
--navy-tint-2: #dde4ee

--amber:       #b45309    /* validity warnings ONLY */
--amber-700:   #92400e
--amber-tint:  #fbf0e1
--amber-line:  #e6c595

--ok:          #3f6b52    /* sparing — checklists */
--ok-tint:     #e8f0ea
```

Sidebar uses an even darker custom navy (`#1a2734`) — not in the variable
set above. Keep that.

**Rules that cannot bend:**
- Amber appears **only** in validity callouts, the persistent banner, "Main
  conclusion" KPI, the Gap multiplier when ≥5×, the "Do NOT" card, and the
  warning tabs. Never as decoration.
- Numbers always use `font-variant-numeric: tabular-nums` and IBM Plex Mono.
  This is a data study — columns must align.
- 14px base body. Compact spacing (8px grid). Cards are 1px-bordered with
  6px radius and a barely-there shadow. No glassmorphism, no gradients on
  surfaces.

### 6.2 ELEVATE — three deliberate refinements

**(a) Typography hierarchy.** Add a third typeface for headings to give the
research a more editorial / monograph feel without losing the system's quiet
restraint. Pair:

- **Fraunces** (variable serif, opsz + soft axis tuned) for H1 page titles only — gives the working-paper masthead feel
- **IBM Plex Sans** for everything else
- **IBM Plex Mono** for numbers, KPI values, table cells, eyebrows, footnotes

Section eyebrows are 10.5px IBM Plex Mono, uppercase, 0.06em tracking. H1
becomes Fraunces 28px, weight 500, opsz 36, soft 30, tight tracking. The
Fraunces only on H1 keeps the contrast intentional — every other heading
stays IBM Plex Sans.

**(b) One signature interaction.** When the RQ3 simulator's label scenario
changes, the channel rows in the allocation table must **re-order with a
smooth FLIP animation** (use `framer-motion` `LayoutGroup` or the equivalent).
This is the moment users physically feel the paper's central finding:
allocations re-rank under plausible label corrections. Make this
animation **slow and intentional** (~500ms ease-out), not snappy. It is the
visualisation of instability.

Don't add motion anywhere else by default. One signature beats five micro.

**(c) Material texture — "paper grain".** Add a very subtle SVG noise overlay
on `--paper` (opacity ≤ 0.03) to suggest the texture of a printed working
paper. Keep it imperceptible at first glance; users only notice it on dark
displays at full brightness. Implement once in the root layout via a fixed
pseudo-element so it doesn't repaint on scroll.

### 6.3 Micro-details worth getting right

- **Focus rings**: navy 3px box-shadow at 20% opacity, no offset, on all
  interactive elements. Tab key must move predictably through every page.
- **Number transitions**: when KPI values change (slider, scenario switch),
  animate the count with `useSpring` or equivalent — 250ms, monospace stays
  put, no layout shift.
- **Custom scrollbar**: 11px wide, paper-tinted thumb (`#d3d0c7`), 3px border
  to embed it in the page. Already in JSX prototype — preserve.
- **Hover on chart bars**: 1px navy outline, no fill change. Tooltip is a
  small white card with 1px border, IBM Plex Mono value, tracking the cursor.
- **Empty states**: when a JSON section is missing, show a hatched placeholder
  with a small "evidence not generated" tag — match the `.ph` style in the
  prototype. Don't show generic spinners.

### 6.4 What this aesthetic is NOT

- Not a SaaS dashboard. No purple gradients, no glass cards, no animated blobs.
- Not Notion / Linear minimal. We have density, charts, footnotes.
- Not Bloomberg dark mode. We are bright, warm-paper, optimistic-about-rigour.
- Not Tailwind defaults. If a class outputs the default Tailwind look, retune
  it.

---

## 7. AI assistant — Gemini integration details

**SDK**: `@google/genai` (the official TypeScript SDK).

**Route**: `app/api/chat/route.ts` — Edge runtime, POST, accepts `{ messages, lang? }`,
streams a `text/event-stream` response back to the client.

**Key resolution** (in order):
1. `process.env.GEMINI_API_KEY` (required)
2. If missing, return 503 with a JSON instruction to set the env var.
   Never crash. Never log the key.

**Model resolution**:
1. `process.env.GEMINI_MODEL`
2. Fallback default: `gemini-2.5-flash-lite`

**System instruction** (constant, server-side only):

> You are an assistant embedded in a research dashboard about the validity
> of a public Multi-Touch Attribution dataset. Answer **only** from the
> evidence provided in the project context block. Do not invent metrics.
> Do not recommend a causal channel winner. Do not claim budget uplift is
> causal. Reply in Vietnamese by default; switch to English if the user
> asks. Be concise and student-friendly. If asked about model training,
> explain that models are trained offline in the reproducible pipeline,
> not in this app.

**Project context block** (always appended to the system instruction):
the compact summary from `prompts/08_ai_assistant.md` (10,000 touchpoints,
2,847 users, 83.63% any-Yes, 49.44% row Yes, AUC 0.4902, etc.). Keep this
in `src/lib/ai/context.ts` as a typed constant so it's reviewable.

**Four example prompts** (Vietnamese), pinned above the input:
1. Tóm tắt kết luận 3 RQ
2. Vì sao conversion rate 83.63% là vấn đề?
3. Có nên dùng dataset này để chọn channel thắng không?
4. Giải thích sensitivity analysis

**Error UX**: API failures show a calm inline message in the chat thread
("Không gọi được Gemini — kiểm tra API key trong .env.local"), not a toast,
not a modal.

---

## 8. Forbidden actions (carried over from Streamlit spec)

- ❌ Do not read raw CSV in the frontend.
- ❌ Do not train models, refit logistic regression, or compute Markov matrices in the browser or on the Next.js server.
- ❌ Do not reconstruct user journeys at runtime.
- ❌ Do not recompute SQL baseline attribution.
- ❌ Do not modify anything outside `app/`.
- ❌ Do not claim a causal channel winner. Do not claim budget uplift is causal.
- ❌ Do not hard-code the Gemini API key. Do not log it. Do not expose it to the client bundle.
- ❌ Do not use Plotly, Bootstrap, ChakraUI, or generic shadcn-default styling unmodified.
- ❌ Do not import the Inter font. Do not default to it.

---

## 9. Suggested file structure

```
app/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # root layout: fonts, theme tokens, persistent banner, sidebar
│   │   ├── page.tsx                # redirect to /overview
│   │   ├── overview/page.tsx
│   │   ├── rq1/page.tsx
│   │   ├── rq2/page.tsx
│   │   ├── rq3/page.tsx
│   │   ├── assistant/page.tsx      # client component shell
│   │   ├── safe/page.tsx
│   │   └── api/chat/route.ts       # Gemini streaming endpoint
│   ├── components/
│   │   ├── shell/                  # Sidebar, ValidityBanner, DataStatusPanel
│   │   ├── primitives/             # KpiCard, Callout, Chip, StabilityBadge, ChartCard, PageHead, Section, Table, NumberInput, RadioGroup, SliderControl, Tabs, Select, PromptChip
│   │   ├── charts/                 # Recharts wrappers themed to tokens: BarChart, HBarChart, GroupedBar
│   │   ├── chat/                   # ChatBubble, ChatInput
│   │   └── motion/                 # FlipList for the simulator
│   ├── lib/
│   │   ├── data/                   # typed JSON loaders + Zod schemas
│   │   ├── ai/                     # Gemini client + system instruction + project context
│   │   ├── simulator/              # math: weights, normalize, deltas, stability score
│   │   └── format.ts               # fmtPct, fmtInt, fmtMoney, fmtDelta
│   └── styles/
│       └── globals.css             # @import IBM Plex + Fraunces, root tokens, base resets
├── data/generated/                 # 5 JSON files (PRESERVED from prototype)
├── mockup-screenshots/             # 6 PNGs (copy from external archive)
├── public/                         # paper-grain.svg, favicon, optional figure exports
├── scripts/prepare_app_data.py     # PRESERVED — pipeline writes to data/generated/
├── package.json
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
└── README.md                       # how to run, env vars, regenerate data
```

---

## 10. Acceptance criteria

When complete, all of the following must hold:

**Functional**
- [ ] `pnpm dev` boots the app at `localhost:3000` with all 6 routes navigable
- [ ] All 5 JSON files load and validate against their Zod schemas; missing/invalid file shows an inline error, never a white screen
- [ ] RQ1 slider drives the gap multiplier, saturation chip, and conclusion text live
- [ ] RQ2 tabs swap chart + table content with no layout shift
- [ ] RQ3 simulator: changing label scenario re-orders the allocation table with the FLIP animation; URL params reflect all input state; equal-split deltas compute correctly
- [ ] Assistant page: works with and without `GEMINI_API_KEY`; streams responses; Vietnamese-by-default
- [ ] Safe Recommendation: workflow row + checklists + bottom callout render at 1440×900 without horizontal scroll

**Design**
- [ ] No `#` followed by 3 or 6 hex digits in any `src/**/*.tsx` — all colours come from CSS variables
- [ ] IBM Plex Sans and Mono are loaded via `next/font`; Fraunces appears only on H1s
- [ ] Amber appears nowhere except validity contexts
- [ ] Paper-grain overlay is present but barely perceptible
- [ ] All six pages spot-check against their PNG mockup at 1440 width
- [ ] Tab order is sensible on every page; focus rings are visible and on-brand

**Code health**
- [ ] `pnpm tsc --noEmit` is clean; `pnpm lint` is clean
- [ ] No `any`. No `as unknown as`. No `// @ts-ignore`.
- [ ] No `useEffect` that fetches data the page already has at build time
- [ ] No client component imported into a server component without `'use client'` on the right boundary
- [ ] Components in `primitives/` are stateless and reusable; pages compose them

**Constraints respected**
- [ ] No raw CSV imports. No model training code. No SQL.
- [ ] No client-side reference to `GEMINI_API_KEY`. `grep -r GEMINI_API_KEY src/app` returns only `api/chat/route.ts`.
- [ ] No causal-winner language anywhere in the UI copy.

---

## 11. External references

The original Streamlit-era prompts and mockups live **outside** this repo at:

```
F:\Sem 4\DAP391\MTA-Data validate\app\prompts\           ← 12 numbered .md files (read for context)
F:\Sem 4\DAP391\MTA-Data validate\app\mockup-screenshots\ ← 6 PNGs (copy into app/mockup-screenshots/)
```

The Streamlit-specific instructions (theme injector, `st.cache_data`, etc.)
are obsolete — translate the *intent* (information hierarchy, page content,
forbidden actions, AI behaviour), not the implementation details.

The existing JSX prototype at `app/script JS/` is the most accurate visual
reference for component composition and copy. Read it. Then delete it before
you start.

---

## 12. Working agreement for the implementer

- **Plan first.** Before writing any code, propose the route map, the
  component primitives list, the data-loading approach, and the
  Tailwind/CSS-variables bridge. Get sign-off.
- **One page at a time** after the shell is built. Build Overview first
  (uses every primitive), then RQ1, RQ2, RQ3, Assistant, Safe.
- **Verify in a browser** at each milestone — type-checks and tests confirm
  code correctness, not feature correctness. Screenshot each page against
  its mockup before declaring it done.
- **Push back** if any instruction here conflicts with the data, the
  mockups, or the JSX prototype. The framing is fixed; specific numbers
  follow the loaded JSON.

When in doubt, default to the quieter, more academic choice. This is a
research artefact dressed as a web app, not a web app dressed as research.
