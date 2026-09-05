import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import { Suspense } from "react";
import Analytics from "@/components/Analytics";
import { ToastProvider } from "@/components/ui/Toast";
import "./globals.css";

const grotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-grotesk",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "StoreScout — Shopify Competitor Monitoring",
  description:
    "Review public prices, product additions and compare-at discounts across supported Shopify stores. Daily checks on Pro, with source-linked results.",
  openGraph: {
    title: "StoreScout — Shopify Competitor Intelligence",
    description: "Always know what your Shopify competitors are doing.",
    siteName: "StoreScout",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${grotesk.variable} ${jetbrains.variable} h-full`}>
      <body className="min-h-full flex flex-col antialiased">
        <ToastProvider>
          {children}
        </ToastProvider>
        <Suspense fallback={null}>
          <Analytics />
        </Suspense>
      </body>
    </html>
  );
}
