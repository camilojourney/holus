import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Observatory API URL for server-side fetches
  env: {
    NEXT_PUBLIC_OBSERVATORY_URL:
      process.env.NEXT_PUBLIC_OBSERVATORY_URL ?? "http://localhost:8001",
  },
};

export default nextConfig;
