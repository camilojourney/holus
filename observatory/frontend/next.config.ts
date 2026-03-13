import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Observatory API URL for server-side fetches
  // Empty string triggers demo mode with mock data on Vercel
  env: {
    NEXT_PUBLIC_OBSERVATORY_URL:
      process.env.NEXT_PUBLIC_OBSERVATORY_URL ?? "",
    NEXT_PUBLIC_DEMO_MODE:
      process.env.NEXT_PUBLIC_DEMO_MODE ?? "true",
  },
};

export default nextConfig;
