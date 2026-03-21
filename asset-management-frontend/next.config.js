/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    // Server-side proxy: /api/* → backend service
    // Dùng tên service "backend" trong Docker network
    const backendUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8080";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;