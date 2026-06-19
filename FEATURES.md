# MTA Data Validity Dashboard — Feature Specification

> Dùng file này để rebuild với bất kỳ design mới nào. Tất cả tính năng, số liệu, logic đều đầy đủ — không cần nhìn lại code cũ.

---

## Cấu trúc tổng thể

**Shell layout**: Sidebar cố định bên trái + vùng nội dung cuộn bên phải.

**Validity banner**: Dải cảnh báo cố định phía trên toàn app — nhắc người dùng đây là validity-audit tool, không phải budget optimizer.

**Sidebar** chứa:
- Brand block (tên project)
- Navigation 6 mục, mỗi mục có index số (01–06), label, và href. Mục "AI Assistant" có badge "beta".
- **Data status panel**: Files loaded 5/5, Touchpoints 10,000, Pipeline v1.3, Last refresh 2026-06-05.

**Navigation items**:
| Index | Label | Href |
|---|---|---|
| 01 | Overview | /overview |
| 02 | RQ1 · Validity Audit | /rq1 |
| 03 | RQ2 · Diagnostics | /rq2 |
| 04 | RQ3 · Simulator | /rq3 |
| 05 | AI Assistant | /assistant |
| 06 | Safe Recommendation | /safe |

---

## Trang 1 — Overview (`/overview`)

**Mục đích**: Tóm tắt nhanh toàn bộ dataset validity ở mức headline.

### KPI Row — 6 thẻ

| Label | Value | Caption / note |
|---|---|---|
| Total touchpoints | 10,000 | rows ingested |
| Users | 2,847 | unique journeys |
| Row-level Yes rate | 49.44% | 4,944 / 10,000 rows |
| User any-Yes conversion | 83.63% | ≥1 Yes per user |
| Row-channel AUC | 0.4902 | ≈ chance (0.50) |
| Main conclusion | "Not safe for direct attribution" | thẻ này dùng warn/amber style |

### Diagnostic panels — grid 2×2 chart cards

**Chart 1 — Conversion rate gap** (vertical bar, tag RQ1):
- Benchmark: 0.03 (grey)
- Row Yes: 0.4944 (warn/amber)
- User any-Yes: 0.8363 (warn/amber)
- Threshold line tại y=0.03, label "3% benchmark"
- Caption: "Observed rates vs. a typical e-commerce benchmark (3%)."

**Chart 2 — Label-event audit** (horizontal bar, tag RQ2):
- Row-level Yes: 0.4944 (warn)
- Final-touch Yes: 0.6120
- Multi-Yes users: 0.6080 (warn)
- Yes before final: 0.5280 (warn)
- Caption: "Where conversion labels concentrate across the journey."

**Chart 3 — Model comparison** (vertical bar, tag RQ2):
- Channel: 0.4902 (warn)
- Journey len: 0.7549 (navy)
- Chan+len: 0.7536 (navy light)
- Threshold line tại y=0.5, label "chance"
- Caption: "Predictive AUC: channel signal vs. journey-length signal."

**Chart 4 — Sensitivity stability** (vertical bar, tag RQ3):
- As-lbl: 0.205
- Final: 0.171
- Dedup: 0.151 (dim)
- Drop-pre: 0.118 (dim)
- Bench: 0.092 (warn)
- Cons.: 0.071 (warn)
- Caption: "Attribution share for Email across 6 label scenarios."

**Footnote**: "All panels derive from the same precomputed pipeline. Charts are diagnostic, not prescriptive — no channel is endorsed as a 'winner'."

---

## Trang 2 — RQ1 Validity Audit (`/rq1`)

**Mục đích**: Định lượng label saturation so với benchmark người dùng tự chọn.

**Câu hỏi nghiên cứu**: "Is the dataset valid enough for direct multi-touch attribution?"

### Benchmark slider

- Range: 1%–10%, step 0.5, default 3%
- Tick marks tại: 1, 3, 5, 10
- Hint: "Typical online retail user-level conversion sits near 2–4%."
- Format display: `X.X%`

### Computed results — 3 thẻ KPI (tính real-time từ slider)

1. **Observed user any-Yes rate** — 83.63% (cố định, không thay đổi)
2. **Selected benchmark threshold** — giá trị slider hiện tại
3. **Gap multiplier** — `83.63% ÷ benchmark_value`:
   - Severity: High nếu gap ≥ 20×, Medium nếu ≥ 10×, Low nếu < 10×
   - Thẻ này đổi màu amber và hiện icon warn khi High
   - Hiển thị Chip với label "High/Medium/Low saturation"

### Evidence table — 4 hàng cố định

| Evidence metric | Value | Interpretation | Concern |
|---|---|---|---|
| Row-level Yes rate | 49.44% | 4,944 of 10,000 touchpoint rows labelled Yes | High |
| Final-touch Yes rate | 61.20% | Share of journeys with a Yes on the final touch | Medium |
| Users with multiple Yes events | 1,731 (60.8%) | A single user records several "conversions" | High |
| Users with Yes before final touch | 1,502 (52.8%) | Label fires mid-journey, not at outcome | High |

Chip severity: High = amber, Medium = yellow, Low = green.

### Dynamic Callout (warn variant, cập nhật theo slider)

Template: "At a **{bench}%** benchmark, the observed **83.63%** user any-Yes rate is **{gap}×** higher than expected. Combined with mid-journey and multi-Yes labelling, this indicates the conversion label is **saturated and not outcome-aligned**. The dataset is **not valid for direct multi-touch attribution**; treat it as a validity-audit artefact instead."

---

## Trang 3 — RQ2 Model Diagnostics (`/rq2`)

**Mục đích**: Kiểm định thống kê chứng minh channel không có signal dự báo.

**Câu hỏi nghiên cứu**: "What evidence shows label bias, weak channel signal, or confounding?"

### View controls (2 Select, không ảnh hưởng logic — chỉ cosmetic)

- **Metric**: AUC / McFadden R² / Positive rate
- **Diagnostic view**: Channel signal / Journey length confounding / Markov removal effect

### 4 Tabs — mỗi tab có layout 2 cột: chart (trái) + data table (phải)

---

**Tab 1 — Channel signal test**

Chart (horizontal bar):
- Cramér's V: 0.0139 (warn)
- Channel AUC: 0.4902 (warn)
- Chance line: 0.500 (grey reference)

Table:
| Metric | Value | Note |
|---|---|---|
| Chi-square p-value | 0.8598 | Channel × conversion independence not rejected |
| Cramér's V | 0.0139 | Effect size ≈ 0 (no association) |
| Row-channel AUC | 0.4902 | Indistinguishable from chance (0.50) |

Interpretation: "Channels carry essentially **no signal** for the row-level label. A chi-square p of **0.8598** and a vanishing effect size mean channel identity does not predict conversion."

---

**Tab 2 — Logistic regression comparison**

Chart (grouped bar, 3 nhóm, 1 series "AUC"):
- Channel only: 0.4902
- Length only: 0.7549
- Channel + length: 0.7536

Table:
| Metric | Value | Note |
|---|---|---|
| Channel-only AUC | 0.4902 | Baseline channel model — at chance |
| Journey-length-only AUC | 0.7549 | Length alone is strongly predictive |
| Channel + length AUC | 0.7536 | Adding channel does not help (−0.0013) |

Interpretation: "Adding channel to a length-only model **fails to improve AUC** (0.7549 → 0.7536). The predictive power lives in journey length, not channel choice."

---

**Tab 3 — Journey-length confounding**

Chart (vertical bar, giống Tab 2 nhưng layout khác):
- Channel: 0.4902 (warn)
- Journey length: 0.7549 (navy)
- Combined: 0.7536 (navy light)
- Threshold line tại 0.5

Table:
| Metric | Value | Note |
|---|---|---|
| Length McFadden R² | 0.2604 | Journey length explains most variance |
| Channel McFadden R² | 0.0021 | Channel explains ≈ nothing |
| Confounder | Journey length | Drives both touch count and labels |

Interpretation: "Journey length is a **confounder**: longer journeys accumulate more touches and more Yes labels, inflating any apparent channel effect. Channel 'performance' is largely a length artefact."

---

**Tab 4 — Markov removal effect**

Chart (horizontal bar, 6 channels):
- Email: 0.061
- Search: 0.058
- Direct: 0.054
- Referral: 0.041
- Social: 0.033
- Display: 0.028

Table:
| Metric | Value | Note |
|---|---|---|
| Removal-effect spread | 0.028 – 0.061 | Narrow band across all channels |
| Max / min ratio | 2.18× | No channel dominates removal effect |
| Stability (Spearman) | 0.43 | Ranking unstable across scenarios |

Interpretation: "Markov removal effects are **tightly clustered** and re-rank under resampling. No channel shows a robust, separable removal effect that would justify causal credit."

---

**Callout info** phía dưới (text đổi theo tab active): kết thúc với "Net: the channel dimension is statistically inert; observed differences trace to journey length and label artefacts, not media effectiveness."

---

## Trang 4 — RQ3 Interactive Simulator (`/rq3`)

**Mục đích**: What-if diagnostic — thay đổi inputs để thấy allocation fragile như thế nào. Không phải budget recommendation.

**Câu hỏi nghiên cứu**: "Given the limitations, what analysis strategy is safer?"

### Layout: 2 cột — Inputs (trái) | Outputs (phải)

---

### Inputs

**Total marketing budget** — NumberInput, prefix "$", step $1,000, min $0

**Revenue per conversion** — NumberInput, prefix "$", step $5, min $0

**Conversion label scenario** — Select, 6 options:

| ID | Name | Multiplier | Note |
|---|---|---|---|
| as-labeled | As-labeled (row Yes = 49.44%) | 1.00 | Raw row-level labels, no correction |
| final-touch | Final-touch label only | 0.74 | Keep only the converting final touch |
| dedup-user | De-dup any-Yes per user (83.63%) | 0.61 | Collapse to one outcome per user |
| drop-pre | Drop pre-final Yes events | 0.55 | Remove Yes occurring before final touch |
| bench-cal | Benchmark-calibrated to 3% | 0.21 | Re-scale to e-commerce prior |
| conservative | Conservative (labels suspect) | 0.16 | Strong shrinkage toward null |

**Attribution method** — Select, 6 options với weights precomputed:

| Method | Direct | Display | Email | Referral | Search | Social | Stability |
|---|---|---|---|---|---|---|---|
| Equal split | 1/6 | 1/6 | 1/6 | 1/6 | 1/6 | 1/6 | 1.00 |
| Row conversion rate weighted | 18.2% | 12.1% | 20.5% | 14.9% | 21.4% | 12.9% | 0.31 |
| Linear | 17.6% | 15.0% | 18.2% | 16.0% | 17.8% | 15.4% | 0.77 |
| First-touch | 12.0% | 23.2% | 11.0% | 15.0% | 15.8% | 23.0% | −0.14 |
| Last-touch | 23.8% | 9.2% | 25.0% | 15.0% | 19.0% | 8.0% | 0.09 |
| Markov | 20.5% | 11.0% | 22.0% | 14.2% | 20.5% | 11.8% | 0.43 |

**Allocation mode** — RadioGroup 2 options:
- **Auto from method** — weights lấy từ method đã chọn
- **Manual channel sliders** — 6 range sliders (0–40, step 1), normalized to 100%

Khi manual mode: hiển thị 6 sliders, mỗi slider có label channel và % normalized real-time.

Channels: Direct Traffic, Display Ads, Email, Referral, Search Ads, Social Media

Channel efficiency (conversions per $1k, precomputed, label-suspect):
- Direct: 2.10, Display: 0.92, Email: 3.35, Referral: 1.78, Search: 2.58, Social: 1.24

---

### Outputs

**Budget allocation table** (6 channel rows + total row):
- Columns: Channel | Weight % | Allocation $ | Est. conversions
- **Signature animation**: khi method hoặc scenario thay đổi, rows re-rank với FLIP animation (Framer Motion LayoutGroup + motion.tr layout, 0.5s cubic-bezier easing)
- **StabilityBadge** (góc trên phải bảng): stable / moderate / unstable
  - stable: Spearman score ≥ 0.70
  - moderate: score ≥ 0.30
  - unstable: score < 0.30

**Compute formula**: `allocation = budget × normalized_weight` | `conversions = (budget × weight / 1000) × channel_efficiency × label_multiplier`

**2 BigNum cards**:
- Estimated conversions (số nguyên formatted)
- Estimated revenue ($ formatted)

**2 Delta cards** (vs equal split baseline):
- Δ conversions: `+N` màu xanh / `−N` màu đỏ / `0` neutral
- Δ revenue: `+$N` / `−$N` / `$0`

**Callout** (warn variant, text đổi theo stabilityState):
- stable: "…ranking is comparatively robust here, but still rests on suspect labels"
- unstable/moderate: "…ranking re-orders under plausible label corrections"

---

## Trang 5 — AI Assistant (`/assistant`)

**Mục đích**: Q&A grounded trong project evidence, powered by Gemini streaming API.

### Chat interface

**Greeting message** (cố định khi load, không thể xoá):
> "Hello — I'm the project research assistant. I answer strictly from this study's precomputed evidence about the MTA dataset's validity. Ask about the three research questions, the 83.63% label issue, or how to present the findings."

**Chat thread** (scroll tự động xuống khi có message mới):
- ChatBubble user (align phải, màu navy)
- ChatBubble assistant (align trái, màu surface)
- Multi-paragraph: split text theo `\n\n`, render mỗi đoạn thành `<p>`

**Typing indicator** (khi streaming): ChatBubble assistant với text italic "Retrieving from evidence…"

**Inline error display** (amber style, không dùng toast):
```
amber background + left border + text "Request failed: 503" hoặc message từ API
```

**4 PromptChip tiếng Việt** (click gửi ngay, không cần nhấn Enter):
1. "Vấn đề với nhãn chuyển đổi là gì?"
2. "Tại sao channel không dự báo được conversion?"
3. "Journey length ảnh hưởng thế nào?"
4. "RQ3 nói gì về độ ổn định?"

**Input bar**:
- Textarea (rows=1, auto-expand)
- Enter gửi, Shift+Enter xuống dòng
- Send button: disabled khi draft rỗng hoặc đang streaming

**Notice bar phía trên chat**: "Powered by Gemini. Answers grounded in project evidence only. May make mistakes."

### Backend — `/api/chat` (POST, Node runtime)

- Đọc `GEMINI_API_KEY` từ `process.env` — **không bao giờ gửi về client**
- 503 nếu thiếu key, kèm hướng dẫn lấy key tại aistudio.google.com/apikey
- `GEMINI_MODEL` từ env hoặc default `gemini-2.5-flash-lite`
- Streaming response: `ReadableStream<Uint8Array>` → `Content-Type: text/plain; charset=utf-8`
- System instruction: tiếng Việt mặc định, constrained to project evidence, no causal claims
- Project context: embed số liệu key vào prompt (AUC, chi-square, etc.)

---

## Trang 6 — Safe Recommendation (`/safe`)

**Mục đích**: Workflow phân tích an toàn và checklist do/don't.

**Câu đề trang**: "Given the limitations, the safer path forward"

### Recommended workflow — 5 bước dạng horizontal flow

```
[STEP 1] → [STEP 2] → [STEP 3] → [STEP 4] → [OUTPUT]
```

| Index | Title | Description |
|---|---|---|
| STEP 1 | Ingest & profile | Load touchpoints, profile label distribution |
| STEP 2 | Validity audit | Test label saturation & channel signal |
| STEP 3 | Confounding check | Separate journey-length from channel |
| STEP 4 | Sensitivity ranges | Re-run across label scenarios |
| OUTPUT | Audit report | Disclose limits — no channel winner |

Bước OUTPUT có visual "terminal" khác biệt (background tối hơn hoặc border đặc biệt).
Mũi tên `→` giữa các bước (không có mũi tên sau OUTPUT).

### 2-col grid — Safer strategies | Do NOT

**Safer analysis strategies** (icon check màu xanh):
1. Use the dataset for validity audit, not direct attribution
2. Treat conversion labels as suspect until validated
3. Report sensitivity ranges, not point estimates
4. Disclose the 83.63% label saturation prominently

**Do NOT** (icon X màu amber, card background amber-tint):
1. Do not claim a causal channel winner
2. Do not optimize budget directly from this dataset
3. Do not use the row-level label for individual attribution

### Info Callout — "Bottom line"

> "This dataset is valuable as a **validity-audit artefact** and a teaching example of label bias — not as a source of causal channel credit. Frame every downstream claim as conditional on resolving the conversion-label problem first."

---

## Data Constants (không thay đổi)

### Study headline numbers

```
touchpoints:    10,000
users:          2,847
rowYesRate:     0.4944   (49.44%)
userAnyYes:     0.8363   (83.63%)
rowChannelAUC:  0.4902
jlenAUC:        0.7549
jlenChAUC:      0.7536
chiP:           0.8598
cramersV:       0.0139
mcfaddenCh:     0.0021
mcfaddenJlen:   0.2604
pipelineVersion: "v1.3"
lastRefresh:    "2026-06-05"
```

### Format rules

- Số nguyên lớn: thousand separator (10,000 / 2,847)
- Tiền: `$` prefix, thousand separator ($100,000)
- Phần trăm: 2 chữ số thập phân (49.44%)
- AUC / ratio: 4 chữ số thập phân (0.4902)
- Delta dương: prefix `+`, delta âm: prefix `−`

---

## Constraints bất biến (enforced)

| Rule | Detail |
|---|---|
| No raw CSV | Chỉ đọc từ 5 JSON precomputed |
| No model training | Không training, không SQL, không journey reconstruction |
| No causal claims | Không viết "channel X wins" hay bất kỳ winner claim |
| API key server-only | `GEMINI_API_KEY` chỉ trong route handler, không ra client |
| Amber = warning only | Màu amber chỉ dùng cho validity warnings, không decorative |
| No direct attribution | UI copy luôn frame kết quả là conditional / diagnostic |
