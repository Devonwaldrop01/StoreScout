import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.shopify.com", pathname: "/**" },
      { protocol: "https", hostname: "**.myshopify.com", pathname: "/**" },
    ],
  },
};

export default nextConfig;
