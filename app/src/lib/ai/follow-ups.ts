import { ASSISTANT_PROMPTS } from "./system-instruction";

const RULES: Array<{ keywords: RegExp; prompts: readonly [string, string] }> = [
  {
    keywords: /83\.63|label|conversion rate|nhan|nhãn/i,
    prompts: [
      "Why is the 83.63% conversion rate a problem?",
      "Should this dataset choose a winning channel?",
    ],
  },
  {
    keywords: /AUC|channel signal|channel-only|kenh|kênh/i,
    prompts: [
      "Should this dataset choose a winning channel?",
      "Explain the sensitivity analysis",
    ],
  },
  {
    keywords: /sensitivity|scenario|rank|Markov|hang|hạng/i,
    prompts: [
      "Explain the sensitivity analysis",
      "Summarize the three RQ conclusions",
    ],
  },
  {
    keywords: /trinh bay|trình bày|present|thay|thầy|giang vien|giảng viên|defend/i,
    prompts: [
      "Summarize the three RQ conclusions",
      "Explain the sensitivity analysis",
    ],
  },
];

export function getFollowUps(reply: string): readonly [string, string] {
  for (const rule of RULES) {
    if (rule.keywords.test(reply)) return rule.prompts;
  }
  return [ASSISTANT_PROMPTS[0]!, ASSISTANT_PROMPTS[3]!];
}
