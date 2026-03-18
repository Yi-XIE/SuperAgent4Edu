/**
 * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially useful
 * for Docker builds.
 */
import "./src/env.js";

const backendBaseURL =
  process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://localhost:8001";
const langgraphBaseURL =
  process.env.NEXT_PUBLIC_LANGGRAPH_BASE_URL ?? "http://localhost:2024";

/** @type {import("next").NextConfig} */
const config = {
  devIndicators: false,
  async rewrites() {
    return [
      {
        source: "/api/langgraph/:path*",
        destination: `${langgraphBaseURL}/:path*`,
      },
      {
        source: "/api/:path((?!auth(?:/|$)).*)",
        destination: `${backendBaseURL}/api/:path`,
      },
    ];
  },
};

export default config;
