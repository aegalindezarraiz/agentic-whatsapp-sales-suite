import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'
import Sidebar from '@/components/sidebar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Agentic Sales Suite',
  description: 'Panel de administración — Agentic WhatsApp Sales Suite',
}

// Mobile nav items
const MOBILE_NAV = [
  { href: '/',              label: 'Dashboard'      },
  { href: '/conversations', label: 'Conversaciones' },
  { href: '/leads',         label: 'Leads'          },
  { href: '/knowledge',     label: 'Conocimiento'   },
  { href: '/settings',      label: 'Config'         },
]

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full">
      <body className={`${inter.className} min-h-full bg-gray-950 text-white`}>
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <header className="md:hidden sticky top-0 z-10 border-b border-gray-800 bg-gray-950/90 backdrop-blur">
              <div className="px-4 h-14 flex items-center gap-4">
                <div className="w-6 h-6 rounded-md bg-green-500 flex items-center justify-center text-black font-bold text-xs">A</div>
                <span className="text-sm font-semibold">Agentic Sales Suite</span>
              </div>
              <nav className="flex px-4 gap-1 pb-2 overflow-x-auto">
                {MOBILE_NAV.map(({ href, label }) => (
                  <Link
                    key={href}
                    href={href}
                    className="whitespace-nowrap px-3 py-1 rounded-md text-xs text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
                  >
                    {label}
                  </Link>
                ))}
              </nav>
            </header>
            <main className="flex-1 px-6 py-8 max-w-5xl">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  )
}
