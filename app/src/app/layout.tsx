import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/shell/Sidebar";
import { ValidityBanner } from "@/components/shell/ValidityBanner";
import { EvidencePath } from "@/components/shell/EvidencePath";

export const metadata: Metadata = {
  title: "MTA Data Validity Dashboard",
  description:
    "Validity audit and scenario-exploration tool for a public Multi-Touch Attribution dataset. Not a causal budget optimizer.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="paper-grain" aria-hidden />
        <div className="app-grid">
          <Sidebar />
          <main className="app-main">
            <ValidityBanner />
            <EvidencePath />
            <div className="scroll-area app-scroll">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
