"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";

const STEPS: ReadonlyArray<{ label: string; href: Route; match: ReadonlyArray<string> }> = [
  { label: "Label saturation", href: "/rq1?benchmark=3.0", match: ["/rq1"] },
  { label: "Weak channel signal", href: "/rq2?lens=signal&view=journey", match: ["/rq2"] },
  {
    label: "Sensitivity instability",
    href: "/rq3?budget=100000&rev=100&scenario=as-labeled&method=Markov&mode=auto&manual=20%2C10%2C25%2C15%2C20%2C10&compare=1&compareMethod=Last-touch&compareScenario=bench-cal",
    match: ["/rq3"],
  },
  { label: "Safe recommendation", href: "/safe", match: ["/safe"] },
];

export function EvidencePath() {
  const pathname = usePathname();
  if (pathname === "/presentation") return null;

  return (
    <div className="evidence-path" aria-label="Evidence path">
      <span className="ep-label">Evidence path</span>
      <div className="ep-steps">
        {STEPS.map((step, index) => {
          const active = step.match.some((path) => pathname === path || pathname?.startsWith(path + "/"));
          return (
            <span className="ep-step-wrap" key={step.label}>
              <Link className={"ep-step" + (active ? " active" : "")} href={step.href}>
                {step.label}
              </Link>
              {index < STEPS.length - 1 ? <span className="ep-arrow">/</span> : null}
            </span>
          );
        })}
      </div>
    </div>
  );
}
