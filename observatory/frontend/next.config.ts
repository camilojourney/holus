import type { NextConfig } from "next";

const OBSERVATORY_API = process.env.NEXT_PUBLIC_OBSERVATORY_URL || "http://localhost:8003";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_OBSERVATORY_URL: OBSERVATORY_API,
    NEXT_PUBLIC_DEMO_MODE: process.env.NEXT_PUBLIC_DEMO_MODE ?? "false",
  },
  // Proxy /api/v1/* to the Observatory API so the browser only needs port 3000
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${OBSERVATORY_API}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
