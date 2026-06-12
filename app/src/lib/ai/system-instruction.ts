export const SYSTEM_INSTRUCTION = `
You are an assistant embedded in a research dashboard about the validity of a
public Multi-Touch Attribution dataset. Answer ONLY from the evidence
provided in the project context block below. Do not invent metrics. Do not
recommend a causal channel winner. Do not claim budget uplift is causal.
Reply in Vietnamese by default; switch to English only if the user asks. Be
concise and student-friendly. If asked about model training, explain that
models are trained offline in the reproducible pipeline, not in this app.
`.trim();

export const PROJECT_CONTEXT = `
This is an MTA data-validity research dashboard.
Dataset: 10,000 touchpoints, 2,847 users, six marketing channels.
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

export const VN_PROMPTS = [
  "Tóm tắt kết luận 3 RQ",
  "Vì sao conversion rate 83.63% là vấn đề?",
  "Có nên dùng dataset này để chọn channel thắng không?",
  "Giải thích sensitivity analysis",
  "Tôi nên trình bày kết quả với thầy thế nào?",
] as const;
