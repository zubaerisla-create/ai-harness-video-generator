/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
      { source: '/VAULT', destination: '/vault', permanent: true },
      { source: '/Vault', destination: '/vault', permanent: true },
      { source: '/STUDIO', destination: '/studio', permanent: true },
      { source: '/Studio', destination: '/studio', permanent: true },
      { source: '/QUEUE', destination: '/queue', permanent: true },
      { source: '/Queue', destination: '/queue', permanent: true },
      { source: '/TELEMETRY', destination: '/telemetry', permanent: true },
      { source: '/Telemetry', destination: '/telemetry', permanent: true },
    ];
  },
};

module.exports = nextConfig;
