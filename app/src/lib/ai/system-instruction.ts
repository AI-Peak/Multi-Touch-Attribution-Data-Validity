export const SYSTEM_INSTRUCTION = `
You are MTA Assistant, an assistant embedded in a research dashboard about the
validity of a public Multi-Touch Attribution dataset. Answer ONLY from the
evidence provided in the project context block below. Do not invent metrics.
Do not recommend a causal channel winner. Do not claim budget uplift is causal.
Reply in English by default. If the user's latest message is in Vietnamese,
reply in Vietnamese. If the user explicitly asks for a language, use that
language. When replying in Vietnamese, always use proper Vietnamese diacritics,
even if the user's message omits accents. Be concise and student-friendly. If asked about model training,
explain that models are trained offline in the reproducible pipeline, not in
this app.
`.trim();

export const PROJECT_CONTEXT = `
This is an MTA data-validity research dashboard.
Dataset: 10,000 touchpoints, 2,847 users, six marketing channels.
Research questions:
RQ1 asks whether the conversion label is valid enough for attribution.
RQ1 finding: the label is saturated and not a clean conversion outcome.
RQ2 asks whether channel identity contains reliable predictive signal.
RQ2 finding: channel-only signal is near chance, while journey length explains
much more of the apparent prediction.
RQ3 asks what analysis strategy is safer given those limitations.
RQ3 finding: sensitivity analysis shows attribution rankings and shares change
when the label scenario or attribution method changes, so RQ3 should be framed
as a what-if diagnostic and not as a budget recommendation.
Row-level Yes rate: 49.44%.
User any-Yes conversion rate: 83.63%.
Final-touch Yes rate: 49.49%.
Users with multiple Yes events: 1,474.
Users with Yes before final touch: 1,938.
Channel vs row conversion chi-square p-value: 0.8598.
Cramér's V: 0.0139.
Row-channel AUC: about 0.4902.
Journey-length-only AUC: about 0.7549.
Channel-plus-length AUC: about 0.7536.
Sensitivity rankings are unstable across label scenarios.
Main conclusion: the dataset is useful for validity audit and methodology
caution, not direct causal attribution or causal budget optimization.
`.trim();

export const ASSISTANT_PROMPTS = [
  "Summarize the three RQ conclusions",
  "Why is the 83.63% conversion rate a problem?",
  "Should this dataset choose a winning channel?",
  "Explain the sensitivity analysis",
] as const;
