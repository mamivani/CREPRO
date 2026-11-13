/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Produces a self-contained .next/standalone server (only the deps the
  // build actually traced) for the Docker image -- see apps/web/Dockerfile.
  output: 'standalone',
  typescript: {
    // Reduce false positives from unused imports on components-only modules
    tsconfigPath: './tsconfig.json',
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003',
    NEXT_PUBLIC_IDENTITY_URL: process.env.NEXT_PUBLIC_IDENTITY_URL || 'http://localhost:8001',
  },
};

module.exports = nextConfig;
