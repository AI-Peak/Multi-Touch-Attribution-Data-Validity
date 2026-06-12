import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono, Fraunces } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/shell/Sidebar";
import { ValidityBanner } from "@/components/shell/ValidityBanner";
import { EvidencePath } from "@/components/shell/EvidencePath";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-sans",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  axes: ["opsz", "SOFT"],
  display: "swap",
});

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
      <body
        className={`${plexSans.variable} ${plexMono.variable} ${fraunces.variable}`}
      >
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
