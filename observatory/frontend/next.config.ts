import type { NextConfig } from "next";

const OBSERVATORY_API = process.env.NEXT_PUBLIC_OBSERVATORY_URL || "http://localhost:8003";
const isPublicDemo = process.env.NODE_ENV === "production" || process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_OBSERVATORY_URL: OBSERVATORY_API,
    NEXT_PUBLIC_DEMO_MODE: isPublicDemo ? "true" : "false",
  },
  async rewrites() {
    if (isPublicDemo) {
      return [];
    }
    return [
      {
        source: "/api/v1/:path*",
        destination: `${OBSERVATORY_API}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
