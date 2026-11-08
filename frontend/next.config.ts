import type { NextConfig } from "next";

// FastAPI backend. The browser only ever talks to Next.js at /api/*, which is
// forwarded here, so cookies stay first-party and no CORS setup is needed.
const API_URL = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
  async headers() {
    // Signed-in pages must never be kept by the browser or its back/forward
    // cache, so Back after logging out cannot show them again.
    return [
      {
        source: "/:area(l1|l2|l3|admin|is|cp)/:path*",
        headers: [{ key: "Cache-Control", value: "no-store" }],
      },
    ];
  },
};

export default nextConfig;
