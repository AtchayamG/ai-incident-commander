/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@incident-commander/contracts"],
  experimental: {
    cpus: 1,
    workerThreads: true,
  },
};

module.exports = nextConfig;
