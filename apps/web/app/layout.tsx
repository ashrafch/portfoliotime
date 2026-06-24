import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "PortfolioTime — Simula il tuo portafoglio nella storia",
  description:
    "Scopri come avrebbe performato il tuo portafoglio durante i grandi scenari storici: crisi del 2008, COVID-19, bolla dotcom e molto altro.",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
