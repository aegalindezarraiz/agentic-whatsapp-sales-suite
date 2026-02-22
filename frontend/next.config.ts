import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Standalone output: imagen Docker mínima (sin node_modules completo en runtime)
  output: 'standalone',
}

export default nextConfig
