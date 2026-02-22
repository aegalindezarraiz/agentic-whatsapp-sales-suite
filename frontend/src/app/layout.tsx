import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Agentic Sales Suite',
  description: 'Panel de administración — Agentic WhatsApp Sales Suite',
}

const NAV = [
  { href: '/', label: 'Dashboard' },
  { href: '/catalog', label: 'Catálogo' },
  { href: '/docs', label: 'Documentos' },
]

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full">
      <body className={`${inter.className} min-h-full`}>
        {/* Top bar */}
        <header className="sticky top-0 z-10 border-b border-gray-800 bg-gray-950/80 backdrop-blur">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-6">
            <span className="text-sm font-semibold text-white tracking-tight">
              Agentic Sales Suite
            </span>
            <nav className="flex items-center gap-1">
              {NAV.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="px-3 py-1.5 rounded-md text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        {/* Page content */}
        <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
