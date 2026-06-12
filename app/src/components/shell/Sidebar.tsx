"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import { PAGES } from "@/lib/data/constants";
import { DataStatusPanel } from "./DataStatusPanel";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sb-brand">
        <div className="mark">
          <div className="glyph">MTA</div>
          <div>
            <div className="name">Data Validity Dashboard</div>
            <div className="sub">Multi-Touch Attribution</div>
          </div>
        </div>
      </div>

      <div className="sb-section-label">Research views</div>
      <nav className="sb-nav">
        {PAGES.map((p) => {
          const isActive =
            pathname === p.href || pathname?.startsWith(p.href + "/");
          return (
            <Link
              key={p.id}
              href={p.href as Route}
              className={`nav-item${isActive ? " active" : ""}`}
            >
              <span className="nav-idx num">{p.idx}</span>
              <span className="nav-label">{p.label}</span>
              {p.tag ? <span className="nav-tag">{p.tag}</span> : null}
            </Link>
          );
        })}
      </nav>

      <div className="sb-spacer" />
      <DataStatusPanel />
    </aside>
  );
}
