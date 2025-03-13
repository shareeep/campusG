/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    appDir: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/users/:path*',
        destination: 'http://user-service:3000/api/users/:path*',
      },
      {
        source: '/api/orders/:path*',
        destination: 'http://order-service:3000/api/orders/:path*',
      },
      {
        source: '/api/payments/:path*',
        destination: 'http://payment-service:3000/api/payments/:path*',
      }
    ]
  },
}

module.exports = nextConfig
