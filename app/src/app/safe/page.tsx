"use client";

import Link from "next/link";
import type { Route } from "next";
import { useMemo, useState } from "react";
import { PageHead } from "@/components/primitives/PageHead";
import { Section } from "@/components/primitives/Section";
import { Callout } from "@/components/primitives/Callout";
import { Chip } from "@/components/primitives/Chip";
import { EvidenceActions } from "@/components/primitives/EvidenceActions";
import { IconArrowR, IconCheck, IconWarn, IconX } from "@/lib/icons";

type Step = {
  id: string;
  idx: string;
  title: string;
  desc: string;
  input: string;
  check: string;
  output: string;
  href: Route;
  hrefLabel: string;
  terminal?: boolean;
};

type ChecklistItem = {
  id: string;
  text: string;
  kind: "do" | "dont";
};

const STEPS: ReadonlyArray<Step> = [
  {
    id: "profile",
    idx: "STEP 1",
    title: "Ingest & profile",
    desc: "Load touchpoints and profile label distribution",
    input: "Raw touchpoint rows and journey identifiers",
    check: "Confirm row count, user count, and data refresh version",
    output: "A fixed evidence base for the dashboard",
    href: "/overview",
    hrefLabel: "Review overview",
  },
  {
    id: "validity",
    idx: "STEP 2",
    title: "Validity audit",
    desc: "Test label saturation and outcome alignment",
    input: "Row-level Yes labels and benchmark conversion prior",
    check: "Compare 83.63% any-Yes against the 3% benchmark",
    output: "A label-validity finding, not an attribution claim",
    href: "/rq1",
    hrefLabel: "Open RQ1 audit",
  },
  {
    id: "confounding",
    idx: "STEP 3",
    title: "Confounding check",
    desc: "Separate journey-length signal from channel signal",
    input: "Channel-only, length-only, and combined model diagnostics",
    check: "Verify that channel adds no lift over journey length",
    output: "A warning that apparent channel effects are length artefacts",
    href: "/rq2",
    hrefLabel: "Open RQ2 diagnostics",
  },
  {
    id: "sensitivity",
    idx: "STEP 4",
    title: "Sensitivity ranges",
    desc: "Re-run interpretation across label scenarios",
    input: "Attribution method, label scenario, budget, and revenue assumptions",
    check: "Look for rank changes and share shrinkage under corrections",
    output: "Ranges and stability language instead of point recommendations",
    href: "/rq3",
    hrefLabel: "Open RQ3 simulator",
  },
  {
    id: "report",
    idx: "OUTPUT",
    title: "Audit report",
    desc: "Disclose limits and avoid a channel winner",
    input: "The three RQ findings and sensitivity evidence",
    check: "Every claim stays conditional on resolving label validity first",
    output: "A defensible presentation narrative for stakeholders",
    href: "/assistant",
    hrefLabel: "Ask the evidence",
    terminal: true,
  },
];

const CHECKLIST: ReadonlyArray<ChecklistItem> = [
  { id: "audit", kind: "do", text: "Use the dataset for validity audit, not direct attribution" },
  { id: "suspect", kind: "do", text: "Treat conversion labels as suspect until validated" },
  { id: "ranges", kind: "do", text: "Report sensitivity ranges, not point estimates" },
  { id: "saturation", kind: "do", text: "Disclose the 83.63% label saturation prominently" },
  { id: "winner", kind: "dont", text: "Do not claim a causal channel winner" },
  { id: "budget", kind: "dont", text: "Do not optimize budget directly from this dataset" },
  { id: "row-label", kind: "dont", text: "Do not use the row-level label for individual attribution" },
];

const WORDING = {
  slide:
    "This dataset is suitable for a validity audit and sensitivity demonstration, but not for direct causal budget allocation. The conversion label is saturated, channel signal is weak, and rankings change under plausible label corrections.",
  report:
    "Downstream attribution claims should be framed as conditional on resolving conversion-label validity. Based on the current evidence, the analysis supports diagnostic reporting and sensitivity ranges, not channel-winner or budget-optimization recommendations.",
} as const;

export default function SafePage() {
  const [activeStepId, setActiveStepId] = useState(STEPS[1]!.id);
  const [checked, setChecked] = useState<ReadonlySet<string>>(
    () => new Set(["audit", "suspect", "winner"]),
  );
  const [wordingMode, setWordingMode] = useState<keyof typeof WORDING>("slide");

  const activeStep = useMemo(
    () => STEPS.find((step) => step.id === activeStepId) ?? STEPS[0]!,
    [activeStepId],
  );

  const progress = Math.round((checked.size / CHECKLIST.length) * 100);

  function toggleItem(id: string) {
    setChecked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="page">
      <PageHead
        eyebrow="Safe recommendation"
        title="Given the limitations, the safer path forward"
        desc="A defensible workflow and a do / do-not checklist that keep conclusions inside what the evidence supports."
      />

      <Section
        title="Recommended analysis workflow"
        right={<Chip kind={activeStep.terminal ? "high" : "neutral"}>{activeStep.idx}</Chip>}
      >
        <div className="flow flow-interactive">
          {STEPS.map((step, i) => (
            <span key={step.id} style={{ display: "flex", alignItems: "stretch", flex: 1 }}>
              <button
                className={
                  "flow-step flow-step-button" +
                  (step.terminal ? " terminal" : "") +
                  (activeStep.id === step.id ? " active" : "")
                }
                onClick={() => setActiveStepId(step.id)}
                type="button"
              >
                <div className="fs-idx">{step.idx}</div>
                <div className="fs-title">{step.title}</div>
                <div className="fs-desc">{step.desc}</div>
              </button>
              {i < STEPS.length - 1 ? (
                <div className="flow-arrow">
                  <IconArrowR size={18} />
                </div>
              ) : null}
            </span>
          ))}
        </div>

        <div className="workflow-detail card card-pad">
          <div className="workflow-copy">
            <div className="eyebrow-mono">{activeStep.idx}</div>
            <h2>{activeStep.title}</h2>
            <p>{activeStep.desc}</p>
            <Link className="drilldown-link" href={activeStep.href}>
              {activeStep.hrefLabel}
              <IconArrowR size={15} />
            </Link>
          </div>
          <div className="workflow-fields">
            <div>
              <span>Input</span>
              <b>{activeStep.input}</b>
            </div>
            <div>
              <span>Check</span>
              <b>{activeStep.check}</b>
            </div>
            <div>
              <span>Output</span>
              <b>{activeStep.output}</b>
            </div>
          </div>
        </div>
      </Section>

      <div className="grid-2" style={{ marginTop: 22, alignItems: "start" }}>
        <div className="card card-pad">
          <div className="checklist-head">
            <span className="section-title">Safer analysis checklist</span>
            <Chip kind={progress === 100 ? "low" : "neutral"}>{progress}% reviewed</Chip>
          </div>
          <div className="interactive-checklist">
            {CHECKLIST.filter((item) => item.kind === "do").map((item) => {
              const done = checked.has(item.id);
              return (
                <button
                  aria-pressed={done}
                  className={"check-row" + (done ? " checked" : "")}
                  key={item.id}
                  onClick={() => toggleItem(item.id)}
                  type="button"
                >
                  <span className="ico"><IconCheck size={16} /></span>
                  {item.text}
                </button>
              );
            })}
          </div>
        </div>

        <div className="card card-pad caution-card">
          <div className="checklist-head">
            <span className="section-title">Do NOT</span>
            <IconWarn size={18} />
          </div>
          <div className="interactive-checklist">
            {CHECKLIST.filter((item) => item.kind === "dont").map((item) => {
              const done = checked.has(item.id);
              return (
                <button
                  aria-pressed={done}
                  className={"check-row danger" + (done ? " checked" : "")}
                  key={item.id}
                  onClick={() => toggleItem(item.id)}
                  type="button"
                >
                  <span className="ico"><IconX size={16} /></span>
                  {item.text}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <Section title="Presentation wording">
        <div className="wording-card card card-pad">
          <div className="segmented">
            <button
              className={wordingMode === "slide" ? "active" : ""}
              onClick={() => setWordingMode("slide")}
              type="button"
            >
              Slide
            </button>
            <button
              className={wordingMode === "report" ? "active" : ""}
              onClick={() => setWordingMode("report")}
              type="button"
            >
              Report
            </button>
          </div>
          <p>{WORDING[wordingMode]}</p>
          <EvidenceActions
            copyText={WORDING[wordingMode]}
            downloadText={WORDING[wordingMode]}
            filename={`safe-${wordingMode}-wording.txt`}
          />
        </div>
      </Section>

      <div style={{ marginTop: 20 }}>
        <Callout variant="info" title="Bottom line">
          This dataset is valuable as a <b>validity-audit artefact</b> and a
          teaching example of label bias, not as a source of causal channel
          credit. Frame every downstream claim as conditional on resolving the
          conversion-label problem first.
        </Callout>
      </div>
    </div>
  );
}
