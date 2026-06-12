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

export function offlineEvidenceAnswer(question: string): string {
  const q = question.toLowerCase();

  if (q.includes("83.63") || q.includes("conversion") || q.includes("label") || q.includes("valid")) {
    return [
      "Theo evidence trong project, van de lon nhat la conversion label bi bao hoa: user any-Yes rate la 83.63% va row-level Yes rate la 49.44%.",
      "Muc nay cao bat thuong so voi benchmark e-commerce 3%, nen label khong nen duoc xem nhu outcome conversion sach cho direct MTA.",
      "Nguon: [RQ1] [Overview]",
    ].join("\n\n");
  }

  if (q.includes("channel") || q.includes("winner") || q.includes("thang") || q.includes("auc") || q.includes("rq2")) {
    return [
      "Khong nen dung dataset nay de chon channel thang. Channel-only AUC chi khoang 0.4902, gan nhu chance, trong khi journey-length-only AUC khoang 0.7549.",
      "Dieu nay cho thay tin hieu nam o journey length va label artifact, khong phai hieu qua channel co the claim causal.",
      "Nguon: [RQ2] [Safe]",
    ].join("\n\n");
  }

  if (q.includes("sensitivity") || q.includes("scenario") || q.includes("markov") || q.includes("rq3") || q.includes("budget")) {
    return [
      "Sensitivity analysis cho thay attribution ranking va share thay doi khi doi label scenario hoac method.",
      "Vi ranking khong on dinh, RQ3 nen duoc trinh bay nhu what-if diagnostic, khong phai budget recommendation.",
      "Nguon: [RQ3] [Safe]",
    ].join("\n\n");
  }

  if (q.includes("trinh bay") || q.includes("present") || q.includes("teacher") || q.includes("thay")) {
    return [
      "Cach trinh bay an toan: day la validity-audit dashboard. Ket luan chinh khong phai channel nao tot nhat, ma la dataset hien tai khong du an toan cho direct causal attribution.",
      "Nen di theo mach: label saturation -> weak channel signal -> sensitivity instability -> safe recommendation.",
      "Nguon: [Overview] [RQ1] [RQ2] [RQ3] [Safe]",
    ].join("\n\n");
  }

  return [
    "Tom tat ngan: project cho thay dataset MTA nay huu ich de audit tinh hop le cua label va minh hoa risk cua attribution, nhung khong nen dung de claim causal channel winner.",
    "Bang chung chinh gom: 83.63% user any-Yes, channel AUC khoang 0.4902, journey-length AUC khoang 0.7549, va ranking nhay cam voi label scenarios.",
    "Nguon: [Overview] [RQ1] [RQ2] [RQ3] [Safe]",
  ].join("\n\n");
}
