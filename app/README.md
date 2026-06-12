# MTA Data Validity Dashboard

A Next.js 16 + TypeScript companion app for the
**Multi-Touch Attribution Data Validity** research package. The dashboard is a
validity-audit and scenario-exploration tool — it does **not** provide causal
budget optimization.

## What it shows

Six pages, one per research view:

1. **Overview** — Dataset KPIs and four diagnostic panels.
2. **RQ1 Validity Audit** — Slider-driven benchmark comparison and label-validity evidence table.
3. **RQ2 Model Diagnostics** — Statistical tests, logistic-regression comparison, journey-length confounding, Markov removal effect.
4. **RQ3 Interactive Simulator** — What-if budget allocation with a stability badge. Channels re-rank with a FLIP animation when the attribution method changes — that animation is the paper's headline finding made tangible.
5. **AI Assistant ("Ask the evidence")** — Gemini-grounded Q&A constrained to project evidence. Vietnamese by default.
6. **Safe Recommendation** — A defensible workflow and a do / do-not checklist.

## Data flow

The app consumes only the five JSON files at `app/data/generated/`, produced
by the pipeline:

```
audit-data.json
attribution-data.json
model-data.json
sensitivity-data.json
simulation-data.json
```

A small preprocessor (`scripts/build-data.mjs`) runs before every `next build`
to sanitize `NaN` tokens, slim the oversized `audit-data.json` (22k rows of
duplicated SQL output → 17 deduplicated metric rows), and emit typed derived
JSON to `src/lib/data/__derived__/`. The pages import only the derived files.

To regenerate the source JSON from the analysis pipeline, run **from the repo
root**:

```powershell
python scripts/run_all.py
```

That single command rebuilds the SQL outputs, Python analysis, model outputs,
and the five app JSON files.

## Run

From inside `app/`:

```powershell
# install once
npm install

# slim derived data (also runs automatically before `build`)
npm run prepare-data

# development server
npm run dev

# production build
npm run build
npm start

# type check
npm run typecheck
```

## Environment

Copy `.env.example` to `.env.local` and fill in your Gemini API key:

```powershell
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

Get a key at <https://aistudio.google.com/apikey>.

Without a key, every page still works; only the AI Assistant returns an inline
"missing key" notice.

## Design system

- **Tokens** in `src/app/globals.css` `:root` (paper, surface, ink, navy,
  amber, ok). Amber is reserved strictly for validity warnings.
- **Typography**: IBM Plex Sans (body), IBM Plex Mono (numbers, eyebrows),
  Fraunces serif (H1 page titles only) — all loaded via `next/font/google`.
- **Charts**: Recharts wrappers in `src/components/charts/` with theme tokens.
- **Signature interaction**: framer-motion `LayoutGroup` + `motion.tr layout`
  on the RQ3 allocation table.

## Code shape

```
src/
├── app/                  # App Router routes + api/chat/route.ts
├── components/
│   ├── shell/            # Sidebar, ValidityBanner, DataStatusPanel
│   ├── primitives/       # KpiCard, Callout, Chip, Tabs, …
│   └── charts/           # BarChart, HBarChart, GroupedBar
├── lib/
│   ├── data/             # Zod schemas + typed loaders + constants
│   ├── ai/               # Gemini system instruction + project context
│   ├── simulator/        # Pure compute for RQ3
│   ├── icons.ts          # Curated lucide-react re-exports
│   └── format.ts         # fmt* helpers
└── styles/               # (currently empty; tokens live in app/globals.css)
```

## Constraints (enforced by review)

- No raw CSV imports — the pipeline produces JSON.
- No model training, no journey reconstruction, no SQL recomputation in the app.
- `GEMINI_API_KEY` is read server-side only (in `src/app/api/chat/route.ts`)
  and never reaches the client bundle.
- No causal channel-winner claims. The UI copy uses negations ("do not claim
  a causal channel winner") only.
