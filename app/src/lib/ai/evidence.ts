import type { Route } from "next";

export type CitationId = "overview" | "rq1" | "rq2" | "rq3" | "safe";

export type Citation = {
  id: CitationId;
  label: string;
  href: Route;
  note: string;
};

export const CITATIONS: Record<CitationId, Citation> = {
  overview: {
    id: "overview",
    label: "Overview",
    href: "/overview",
    note: "Dataset scope and headline conclusion",
  },
  rq1: {
    id: "rq1",
    label: "RQ1",
    href: "/rq1",
    note: "Label saturation and validity audit",
  },
  rq2: {
    id: "rq2",
    label: "RQ2",
    href: "/rq2",
    note: "Weak channel signal and confounding diagnostics",
  },
  rq3: {
    id: "rq3",
    label: "RQ3",
    href: "/rq3",
    note: "Scenario sensitivity and what-if simulation",
  },
  safe: {
    id: "safe",
    label: "Safe",
    href: "/safe",
    note: "Safe recommendation boundaries",
  },
};

const citationRules: ReadonlyArray<{
  id: CitationId;
  terms: ReadonlyArray<string>;
}> = [
  {
    id: "rq1",
    terms: ["rq1", "83.63", "49.44", "conversion", "label", "benchmark", "saturation", "validity"],
  },
  {
    id: "rq2",
    terms: ["rq2", "auc", "cramer", "channel", "journey", "confounding", "logistic", "signal"],
  },
  {
    id: "rq3",
    terms: ["rq3", "sensitivity", "scenario", "markov", "simulator", "budget", "ranking", "allocation"],
  },
  {
    id: "safe",
    terms: ["safe", "recommend", "winner", "causal", "claim", "present", "thuyet trinh", "trinh bay"],
  },
];

export function inferCitationIds(text: string): CitationId[] {
  const lower = text.toLowerCase();
  const ids = citationRules
    .filter((rule) => rule.terms.some((term) => lower.includes(term)))
    .map((rule) => rule.id);
  if (ids.length === 0) return ["overview"];
  return Array.from(new Set(ids));
}

export function citationsForText(text: string): Citation[] {
  return inferCitationIds(text).map((id) => CITATIONS[id]);
}

export function shouldReplyInVietnamese(text: string): boolean {
  const lower = text.toLowerCase();
  return (
    /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(text) ||
    /\b(la gi|vi sao|giai thich|tom tat|co nen|khong|du lieu|tieng viet|nhan|kenh|trinh bay|van de|ban|toi|minh|ten gi|la ai|xin chao|chao|goi y|nen hoi gi|phan bo|the nao|nhi|giup)\b/.test(lower)
  );
}

const BUDGET_CHANNELS = [
  "Direct Traffic",
  "Display Ads",
  "Email",
  "Referral",
  "Search Ads",
  "Social Media",
] as const;

function isBudgetQuestion(text: string): boolean {
  const q = text.toLowerCase();
  return /\b(budget|allocate|allocation|split|spend|vnd|dong|phan bo|ngan sach|đầu tư|dau tu)\b/.test(q);
}

function parseBudgetAmount(text: string): number | null {
  const normalized = text.replace(/,/g, "");
  const match = normalized.match(/\b(\d+(?:\.\d+)?)\s*(?:vnd|dong|đ)?\b/i);
  if (!match) return null;
  const amount = Number(match[1]);
  return Number.isFinite(amount) && amount > 0 ? amount : null;
}

function equalSplitLines(amount: number): string[] {
  const rounded = Math.round(amount);
  const base = Math.floor(rounded / BUDGET_CHANNELS.length);
  let remainder = rounded - base * BUDGET_CHANNELS.length;
  return BUDGET_CHANNELS.map((channel) => {
    const value = base + (remainder > 0 ? 1 : 0);
    remainder -= 1;
    return `- ${channel}: ${value.toLocaleString("en-US")} VND`;
  });
}

function compactQuestion(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isGreeting(text: string): boolean {
  const q = compactQuestion(text);
  return /^(hi|hello|hey|xin chao|chao|chao ban|alo|alo ban oi)$/.test(q);
}

function isIdentityQuestion(text: string): boolean {
  const q = compactQuestion(text);
  return /\b(ban ten gi|ten ban la gi|ban la ai|who are you|what is your name|your name|gioi thieu ban than|gioi thieu ve ban)\b/.test(q);
}

function isHelpQuestion(text: string): boolean {
  const q = compactQuestion(text);
  return /\b(help|what can i ask|what should i ask|goi y|goi y cau hoi|toi nen hoi gi|nen hoi gi|huong dan|help me)\b/.test(q);
}

function isOffTopicQuestion(text: string): boolean {
  const q = compactQuestion(text);
  return /\b(bitcoin|weather|thoi tiet|football|bong da|stock price|crypto|facebook ads scrape|scrape facebook|hack|joke|poem|recipe|nau an)\b/.test(q);
}

function isVagueProjectQuestion(text: string): boolean {
  const q = compactQuestion(text);
  return /\b(project|du an|dashboard|mta|dataset|data|attribution|assistant|chatbot|nghien cuu|research)\b/.test(q);
}

function greetingAnswer(vi: boolean): string {
  return vi
    ? [
        "Xin chào, mình là MTA Assistant.",
        "Mình có thể giúp bạn hỏi về RQ1 label validity, RQ2 channel signal/confounding, RQ3 sensitivity analysis, và safe recommendation.",
        "Bạn có thể hỏi: \"RQ3 là gì?\", \"Vì sao 83.63% là vấn đề?\", hoặc \"Có nên chọn channel thắng không?\"",
      ].join("\n\n")
    : [
        "Hi, I am MTA Assistant.",
        "I can help with RQ1 label validity, RQ2 channel signal/confounding, RQ3 sensitivity analysis, and safe recommendations.",
        "Try asking: \"What is RQ3?\", \"Why is 83.63% a problem?\", or \"Should this dataset choose a winning channel?\"",
      ].join("\n\n");
}

function identityAnswer(vi: boolean): string {
  return vi
    ? [
        "Mình là MTA Assistant, trợ lý hỏi đáp cho dashboard Multi-Touch Attribution Data Validity.",
        "Mình chỉ trả lời dựa trên evidence của project: RQ1 về label validity, RQ2 về channel signal/confounding, RQ3 về sensitivity analysis và safe recommendation. Mình không browse web và không đưa khuyến nghị ngân sách thật.",
        "Bạn có thể hỏi: \"RQ3 là gì?\", \"Vì sao 83.63% là vấn đề?\", hoặc \"Tôi có 1100 VND, phân bổ thế nào?\"",
      ].join("\n\n")
    : [
        "I am MTA Assistant, a project-grounded assistant for the Multi-Touch Attribution Data Validity dashboard.",
        "I answer only from this project's evidence: RQ1 on label validity, RQ2 on channel signal/confounding, and RQ3 on sensitivity analysis and safe recommendations. I do not browse the web or provide real budget recommendations.",
        "You can ask: \"What is RQ3?\", \"Why is 83.63% a problem?\", or \"I have 1100 VND, how should I allocate it?\"",
      ].join("\n\n");
}

function helpAnswer(vi: boolean): string {
  return vi
    ? [
        "Bạn có thể hỏi MTA Assistant theo 4 nhóm:",
        "- RQ1: \"Vì sao conversion rate 83.63% là vấn đề?\"\n- RQ2: \"Có nên dùng dataset này để chọn channel thắng không?\"\n- RQ3: \"Sensitivity analysis nói gì?\"\n- Safe/demo: \"Tôi có 1100 VND, phân bổ thế nào?\"",
        "Mình sẽ giữ câu trả lời trong evidence của project và nhắc rõ đâu là diagnostic, đâu là điều không nên claim.",
      ].join("\n\n")
    : [
        "You can ask MTA Assistant in four useful groups:",
        "- RQ1: \"Why is the 83.63% conversion rate a problem?\"\n- RQ2: \"Should this dataset choose a winning channel?\"\n- RQ3: \"What does sensitivity analysis show?\"\n- Safe/demo: \"I have 1100 VND, how should I allocate it?\"",
        "I will keep answers grounded in project evidence and make clear what is diagnostic versus what should not be claimed.",
      ].join("\n\n");
}

function offTopicAnswer(vi: boolean): string {
  return vi
    ? [
        "MTA Assistant chỉ trả lời dựa trên evidence của dashboard MTA Data Validity, nên mình không xử lý câu hỏi ngoài project này.",
        "Nếu muốn, mình có thể giúp bạn nối câu hỏi đó về data validity, attribution risk, RQ1, RQ2, hoặc RQ3.",
      ].join("\n\n")
    : [
        "MTA Assistant only answers from the MTA Data Validity dashboard evidence, so I cannot handle that off-topic request here.",
        "I can help connect your question back to data validity, attribution risk, RQ1, RQ2, or RQ3.",
      ].join("\n\n");
}

function vagueProjectAnswer(vi: boolean): string {
  return vi
    ? [
        "Bạn muốn đi theo hướng nào của project?",
        "- RQ1: label có đáng tin không\n- RQ2: channel có signal thật không\n- RQ3: nên dùng sensitivity/what-if diagnostic như thế nào\n- Safe: nên và không nên claim gì khi trình bày",
        "Nếu bạn hỏi cụ thể hơn, mình sẽ trả lời bằng evidence và số liệu của project.",
      ].join("\n\n")
    : [
        "Which part of the project do you want to inspect?",
        "- RQ1: whether the label is valid\n- RQ2: whether channel identity has reliable signal\n- RQ3: how to use sensitivity and what-if diagnostics safely\n- Safe: what to claim or avoid in the presentation",
        "Ask a more specific question and I will answer from the project evidence.",
      ].join("\n\n");
}

export function shouldUseLocalEvidenceAnswer(question: string): boolean {
  return (
    isGreeting(question) ||
    isIdentityQuestion(question) ||
    isHelpQuestion(question) ||
    isBudgetQuestion(question) ||
    isOffTopicQuestion(question) ||
    isVagueProjectQuestion(question)
  );
}

export function hasSpecificOfflineEvidenceAnswer(question: string): boolean {
  const q = question.toLowerCase();
  return (
    shouldUseLocalEvidenceAnswer(question) ||
    q.includes("83.63") ||
    q.includes("conversion") ||
    q.includes("label") ||
    q.includes("valid") ||
    q.includes("channel") ||
    q.includes("winner") ||
    q.includes("thang") ||
    q.includes("auc") ||
    q.includes("rq1") ||
    q.includes("rq2") ||
    q.includes("rq3") ||
    q.includes("sensitivity") ||
    q.includes("scenario") ||
    q.includes("markov") ||
    q.includes("budget") ||
    q.includes("trinh bay") ||
    q.includes("present") ||
    q.includes("teacher") ||
    q.includes("thay")
  );
}

export function offlineEvidenceAnswer(question: string): string {
  const q = question.toLowerCase();
  const vi = shouldReplyInVietnamese(question);

  if (isGreeting(question)) return greetingAnswer(vi);

  if (isIdentityQuestion(question)) return identityAnswer(vi);

  if (isHelpQuestion(question)) return helpAnswer(vi);

  if (isBudgetQuestion(question)) {
    const amount = parseBudgetAmount(question);
    const split = amount ? equalSplitLines(amount) : [];
    return vi
      ? [
          "MTA Assistant không nên đưa khuyến nghị phân bổ ngân sách thật từ dataset này, vì attribution ranking không ổn định và dataset không có bằng chứng causal như spend, revenue, saturation hay holdout.",
          amount
            ? `Nếu chỉ muốn minh họa trong RQ3 simulator, có thể dùng equal-split baseline cho ${Math.round(amount).toLocaleString("en-US")} VND:\n${split.join("\n")}`
            : "Nếu chỉ muốn minh họa trong RQ3 simulator, hãy dùng equal-split baseline và so sánh với các scenario/method khác.",
          "Đây là baseline chẩn đoán, không phải khuyến nghị đầu tư. Nguồn: [RQ3] [Safe]",
        ].join("\n\n")
      : [
          "MTA Assistant should not give a real budget recommendation from this dataset, because attribution rankings are unstable and the dataset lacks causal evidence such as spend, revenue, saturation, or holdout tests.",
          amount
            ? `For a diagnostic-only RQ3 simulator baseline, you can split ${Math.round(amount).toLocaleString("en-US")} VND evenly across the six channels:\n${split.join("\n")}`
            : "For a diagnostic-only RQ3 simulator baseline, use an equal split and compare it with other scenarios or methods.",
          "This is a diagnostic baseline, not an investment recommendation. Sources: [RQ3] [Safe]",
        ].join("\n\n");
  }

  if (q.includes("83.63") || q.includes("conversion") || q.includes("label") || q.includes("valid")) {
    return vi
      ? [
          "Theo evidence trong project, vấn đề lớn nhất là conversion label bị bão hòa: user any-Yes rate là 83.63% và row-level Yes rate là 49.44%.",
          "Mức này cao bất thường so với benchmark e-commerce 3%, nên label không nên được xem như outcome conversion sạch cho direct MTA.",
          "Nguồn: [RQ1] [Overview]",
        ].join("\n\n")
      : [
          "The main validity issue is label saturation: the user any-Yes rate is 83.63%, and the row-level Yes rate is 49.44%.",
          "That is unusually high compared with a 3% e-commerce benchmark, so the label should not be treated as a clean conversion outcome for direct MTA.",
          "Sources: [RQ1] [Overview]",
        ].join("\n\n");
  }

  if (q.includes("channel") || q.includes("winner") || q.includes("thang") || q.includes("auc") || q.includes("rq2")) {
    return vi
      ? [
          "Không nên dùng dataset này để chọn channel thắng. Channel-only AUC chỉ khoảng 0.4902, gần như chance, trong khi journey-length-only AUC khoảng 0.7549.",
          "Điều này cho thấy tín hiệu nằm ở journey length và label artifact, không phải hiệu quả channel có thể claim causal.",
          "Nguồn: [RQ2] [Safe]",
        ].join("\n\n")
      : [
          "This dataset should not be used to choose a winning channel. Channel-only AUC is about 0.4902, near chance, while journey-length-only AUC is about 0.7549.",
          "That suggests the apparent signal comes from journey length and label artifacts, not a causal channel effect.",
          "Sources: [RQ2] [Safe]",
        ].join("\n\n");
  }

  if (q.includes("sensitivity") || q.includes("scenario") || q.includes("markov") || q.includes("rq3") || q.includes("budget")) {
    return vi
      ? [
          "Sensitivity analysis cho thấy attribution ranking và share thay đổi khi đổi label scenario hoặc method.",
          "Vì ranking không ổn định, RQ3 nên được trình bày như what-if diagnostic, không phải budget recommendation.",
          "Nguồn: [RQ3] [Safe]",
        ].join("\n\n")
      : [
          "Sensitivity analysis shows that attribution rankings and shares change when the label scenario or attribution method changes.",
          "Because the rankings are unstable, RQ3 should be framed as a what-if diagnostic, not as a budget recommendation.",
          "Sources: [RQ3] [Safe]",
        ].join("\n\n");
  }

  if (q.includes("trinh bay") || q.includes("present") || q.includes("teacher") || q.includes("thay")) {
    return vi
      ? [
          "Cách trình bày an toàn: đây là validity-audit dashboard. Kết luận chính không phải channel nào tốt nhất, mà là dataset hiện tại không đủ an toàn cho direct causal attribution.",
          "Nên đi theo mạch: label saturation -> weak channel signal -> sensitivity instability -> safe recommendation.",
          "Nguồn: [Overview] [RQ1] [RQ2] [RQ3] [Safe]",
        ].join("\n\n")
      : [
          "A safe presentation frame is: this is a validity-audit dashboard. The main conclusion is not which channel is best, but that the current dataset is not safe for direct causal attribution.",
          "Use this flow: label saturation -> weak channel signal -> sensitivity instability -> safe recommendation.",
          "Sources: [Overview] [RQ1] [RQ2] [RQ3] [Safe]",
        ].join("\n\n");
  }

  if (isOffTopicQuestion(question)) return offTopicAnswer(vi);

  if (isVagueProjectQuestion(question)) return vagueProjectAnswer(vi);

  return vi
    ? [
        "Tóm tắt ngắn: project cho thấy dataset MTA này hữu ích để audit tính hợp lệ của label và minh họa risk của attribution, nhưng không nên dùng để claim causal channel winner.",
        "Bằng chứng chính gồm: 83.63% user any-Yes, channel AUC khoảng 0.4902, journey-length AUC khoảng 0.7549, và ranking nhạy cảm với label scenarios.",
        "Nguồn: [Overview] [RQ1] [RQ2] [RQ3] [Safe]",
      ].join("\n\n")
    : [
        "Short summary: this MTA dataset is useful for auditing label validity and showing attribution risk, but it should not be used to claim a causal channel winner.",
        "The main evidence is: 83.63% user any-Yes rate, channel AUC around 0.4902, journey-length AUC around 0.7549, and rankings that are sensitive to label scenarios.",
        "Sources: [Overview] [RQ1] [RQ2] [RQ3] [Safe]",
      ].join("\n\n");
}
