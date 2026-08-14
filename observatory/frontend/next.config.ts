import type { NextConfig } from "next";

const OBSERVATORY_API = process.env.NEXT_PUBLIC_OBSERVATORY_URL || "http://localhost:8003";
const isLocalApi = /localhost|127\.0\.0\.1|\[::1\]/i.test(OBSERVATORY_API);

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_OBSERVATORY_URL: OBSERVATORY_API,
    NEXT_PUBLIC_DEMO_MODE: process.env.NEXT_PUBLIC_DEMO_MODE ?? "false",
  },
  // Never proxy the public deployment to a localhost Observatory API.
  async rewrites() {
    if (process.env.NODE_ENV === "production" && isLocalApi) {
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
