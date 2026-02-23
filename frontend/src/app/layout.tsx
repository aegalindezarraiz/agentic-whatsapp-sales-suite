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
  { href: '/', label: 'Dashboard', icon: '◈' },
  { href: '/catalog', label: 'Catálogo', icon: '⊞' },
  { href: '/docs', label: 'Documentos', icon: '⊟' },
  { href: '/conversations', label: 'Conversaciones', icon: '◉' },
  { href: '/settings', label: 'Configuración', icon: '◎' },
  ]

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
          <html lang="es" className="h-full">
                <body className={`${inter.className} min-h-full bg-gray-950 text-white`}>
                  {/* Sidebar + Main layout */}
                        <div className="flex min-h-screen">
                          {/* Sidebar */}
                                  <aside className="hidden md:flex flex-col w-60 border-r border-gray-800/60 bg-gray-950 sticky top-0 h-screen">
                                    {/* Logo */}
                                              <div className="flex items-center gap-2.5 px-5 h-16 border-b border-gray-800/60">
                                                            <div className="w-7 h-7 rounded-lg bg-green-500 flex items-center justify-center text-black font-bold text-sm">A</div>div>
                                                            <div>
                                                                            <p className="text-sm font-semibold text-white leading-tight">Agentic</p>p>
                                                                            <p className="text-xs text-gray-500 leading-tight">Sales Suite</p>p>
                                                            </div>div>
                                              </div>div>
                                    {/* Nav */}
                                              <nav className="flex-1 px-3 py-4 space-y-0.5">
                                                {NAV.map(({ href, label, icon }) => (
                            <Link
                                                key={href}
                                                href={href}
                                                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800/60 transition-colors group"
                                              >
                                              <span className="text-base opacity-60 group-hover:opacity-100 transition-opacity">{icon}</span>span>
                              {label}
                            </Link>Link>
                          ))}
                                              </nav>nav>
                                    {/* Footer */}
                                              <div className="px-5 py-4 border-t border-gray-800/60">
                                                            <div className="flex items-center gap-2">
                                                                            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                                                                            <span className="text-xs text-gray-500">API conectada</span>span>
                                                            </div>div>
                                              </div>div>
                                  </aside>aside>
                        
                          {/* Main content */}
                                  <div className="flex-1 flex flex-col min-w-0">
                                    {/* Mobile header */}
                                              <header className="md:hidden sticky top-0 z-10 border-b border-gray-800 bg-gray-950/90 backdrop-blur">
                                                            <div className="px-4 h-14 flex items-center gap-4">
                                                                            <div className="w-6 h-6 rounded-md bg-green-500 flex items-center justify-center text-black font-bold text-xs">A</div>div>
                                                                            <span className="text-sm font-semibold">Agentic Sales Suite</span>span>
                                                            </div>div>
                                                            <nav className="flex px-4 gap-1 pb-2 overflow-x-auto">
                                                              {NAV.map(({ href, label }) => (
                              <Link
                                                    key={href}
                                                    href={href}
                                                    className="whitespace-nowrap px-3 py-1 rounded-md text-xs text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
                                                  >
                                {label}
                              </Link>Link>
                            ))}
                                                            </nav>nav>
                                              </header>header>
                                  
                                              <main className="flex-1 px-6 py-8 max-w-5xl">
                                                {children}
                                              </main>main>
                                  </div>div>
                        </div>div>
                </body>body>
          </html>html>
        )
}</html>
