"use client";

import Link from "next/link";
import type { Route } from "next";
import { useEffect, useState } from "react";
import { Chip } from "@/components/primitives/Chip";
import { IconArrowR } from "@/lib/icons";

type Slide = {
  eyebrow: string;
  title: string;
  claim: string;
  evidence: ReadonlyArray<readonly [string, string]>;
  href: Route;
  cta: string;
};

const slides: ReadonlyArray<Slide> = [
  {
    eyebrow: "Opening",
    title: "This is a validity audit, not a budget optimizer",
    claim: "The dashboard demonstrates why the dataset should be treated as a diagnostic artefact before any attribution claim.",
    evidence: [
      ["Dataset", "10,000 touchpoints / 2,847 users"],
      ["Main risk", "Conversion-label validity"],
      ["Safe frame", "Audit first, attribution later"],
    ],
    href: "/overview" as Route,
    cta: "Open overview",
  },
  {
    eyebrow: "RQ1",
    title: "The conversion label is saturated",
    claim: "A user any-Yes rate of 83.63% is far above a realistic benchmark and weakens direct MTA validity.",
    evidence: [
      ["User any-Yes", "83.63%"],
      ["Benchmark", "3.0%"],
      ["Gap", "27.9x"],
    ],
    href: "/rq1?benchmark=3.0" as Route,
    cta: "Show RQ1",
  },
  {
    eyebrow: "RQ2",
    title: "Channel signal is weak after diagnostics",
    claim: "Channel-only AUC sits near chance, while journey length carries the stronger predictive signal.",
    evidence: [
      ["Channel AUC", "0.4902"],
      ["Journey length AUC", "0.7549"],
      ["Channel lift", "none"],
    ],
    href: "/rq2?lens=signal&view=journey" as Route,
    cta: "Show RQ2",
  },
  {
    eyebrow: "RQ3",
    title: "Rankings move under method and label changes",
    claim: "Compare mode makes the instability visible: channel shares and ranks shift when method or label scenario changes.",
    evidence: [
      ["Base", "Markov / as-labelled"],
      ["Compare", "Last-touch / benchmark-calibrated"],
      ["Interpretation", "Diagnostic only"],
    ],
    href: "/rq3?budget=100000&rev=100&scenario=as-labeled&method=Markov&mode=auto&manual=20%2C10%2C25%2C15%2C20%2C10&compare=1&compareMethod=Last-touch&compareScenario=bench-cal" as Route,
    cta: "Show compare mode",
  },
  {
    eyebrow: "Recommendation",
    title: "The safe output is a bounded audit report",
    claim: "The defensible claim is conditional: resolve label validity before channel-winner or budget-optimization decisions.",
    evidence: [
      ["Do", "Report sensitivity ranges"],
      ["Do not", "Claim causal winner"],
      ["Output", "Audit report"],
    ],
    href: "/safe" as Route,
    cta: "Show safe path",
  },
];

export default function PresentationPage() {
  const [index, setIndex] = useState(0);
  const slide = slides[index] ?? slides[0]!;
  const isFirst = index === 0;
  const isLast = index === slides.length - 1;

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "ArrowRight") setIndex((current) => Math.min(slides.length - 1, current + 1));
      if (event.key === "ArrowLeft") setIndex((current) => Math.max(0, current - 1));
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="presentation-page">
      <div className="presentation-topbar">
        <div>
          <span className="eyebrow-mono">MTA Data Validity Dashboard</span>
          <h1>Presentation Mode</h1>
        </div>
        <Chip kind="neutral">{index + 1} / {slides.length}</Chip>
      </div>

      <main className="presentation-stage">
        <section className="presentation-copy">
          <div className="eyebrow-mono">{slide.eyebrow}</div>
          <h2>{slide.title}</h2>
          <p>{slide.claim}</p>
          <div className="presentation-actions">
            <Link className="drilldown-link" href={slide.href}>
              {slide.cta}
              <IconArrowR size={16} />
            </Link>
            <Link className="presentation-secondary" href="/overview">
              Exit presentation
            </Link>
          </div>
        </section>

        <section className="presentation-evidence">
          {slide.evidence.map(([label, value]) => (
            <div className="presentation-metric" key={label}>
              <span>{label}</span>
              <b>{value}</b>
            </div>
          ))}
        </section>
      </main>

      <div className="presentation-nav">
        <button disabled={isFirst} onClick={() => setIndex((current) => Math.max(0, current - 1))} type="button">
          Previous
        </button>
        <div className="presentation-dots" aria-label="Presentation progress">
          {slides.map((item, slideIndex) => (
            <button
              aria-label={item.eyebrow}
              className={slideIndex === index ? "active" : ""}
              key={item.eyebrow}
              onClick={() => setIndex(slideIndex)}
              type="button"
            />
          ))}
        </div>
        <button disabled={isLast} onClick={() => setIndex((current) => Math.min(slides.length - 1, current + 1))} type="button">
          Next evidence
        </button>
      </div>
    </div>
  );
}
