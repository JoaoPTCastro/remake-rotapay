import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() { return [{source:"/e",headers:[{key:"Referrer-Policy",value:"no-referrer"},{key:"X-Robots-Tag",value:"noindex, nofollow, noarchive"},{key:"Cache-Control",value:"private, no-store"}]}]; },
  experimental: { serverActions: { bodySizeLimit: "11mb" } },
};

export default nextConfig;
