import type { Metadata } from "next";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
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
    <html lang="en" className={`${jakarta.variable} ${jetbrains.variable} h-full`}>
      <body className="min-h-full flex flex-col antialiased">{children}</body>
    </html>
  );
}
