import { VN_PROMPTS } from "./system-instruction";

const RULES: Array<{ keywords: RegExp; prompts: readonly [string, string] }> = [
  {
    keywords: /83\.63|label|conversion rate|nhãn/i,
    prompts: [
      "Vì sao conversion rate 83.63% là vấn đề?",
      "Có nên dùng dataset này để chọn channel thắng không?",
    ],
  },
  {
    keywords: /AUC|channel signal|channel-only|kênh/i,
    prompts: [
      "Có nên dùng dataset này để chọn channel thắng không?",
      "Giải thích sensitivity analysis",
    ],
  },
  {
    keywords: /sensitivity|scenario|rank|Markov|hạng/i,
    prompts: [
      "Giải thích sensitivity analysis",
      "Tôi nên trình bày kết quả với thầy thế nào?",
    ],
  },
  {
    keywords: /trình bày|present|thầy|giảng viên|defend/i,
    prompts: [
      "Tóm tắt kết luận 3 RQ",
      "Giải thích sensitivity analysis",
    ],
  },
];

export function getFollowUps(reply: string): readonly [string, string] {
  for (const rule of RULES) {
    if (rule.keywords.test(reply)) return rule.prompts;
  }
  return [VN_PROMPTS[0]!, VN_PROMPTS[3]!];
}
