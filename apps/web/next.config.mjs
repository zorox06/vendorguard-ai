/** Next.js configuration with internal backend proxying for unified Docker container. */
const nextConfig = {
  distDir: process.env.VENDORGUARD_BUILD_CHECK === "1" ? ".next-check" : ".next",
  async rewrites() {
    const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
      {
        source: "/ready",
        destination: `${backendUrl}/ready`,
      },
    ];
  },
};
export default nextConfig;
