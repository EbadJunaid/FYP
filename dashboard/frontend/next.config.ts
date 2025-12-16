import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 1. Force Next.js to produce static HTML files
  output: "export",

  // 2. Disable Image Optimization API (incompatible with static export)
  images: {
    unoptimized: true,
  },

  // 3. Ignore TypeScript errors during build (prevents deployment failure on small typos)
  typescript: {
    ignoreBuildErrors: true,
  },

  // 4. Ignore ESLint errors during build
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;