import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import { Suspense } from "react";
import Analytics from "@/components/Analytics";
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
  title: "StoreScout — Track Any Shopify Competitor",
  description:
    "Monitor prices, launches, and discounts across any Shopify store. Get alerted the moment your competitors make a move.",
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
        {children}
        <Suspense fallback={null}>
          <Analytics />
        </Suspense>
      </body>
    </html>
  );
}
