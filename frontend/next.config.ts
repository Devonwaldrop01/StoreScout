import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiUrl}/api/v1/:path*`,
      },
      {
        source: "/check_store",
        destination: `${apiUrl}/check_store`,
      },
    ];
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.shopify.com", pathname: "/**" },
      { protocol: "https", hostname: "**.myshopify.com", pathname: "/**" },
    ],
  },
};

export default nextConfig;
