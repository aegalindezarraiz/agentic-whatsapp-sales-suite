'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

// ── SVG Icons ────────────────────────────────────────────────────────

function IconDashboard({ className }: { className?: string }) {
    return (
          <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                  <rect x="3" y="3" width="7" height="7" rx="1" />
                  <rect x="14" y="3" width="7" height="7" rx="1" />
                  <rect x="3" y="14" width="7" height="7" rx="1" />
                  <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>svg>
        )
}

function IconChat({ className }: { className?: string }) {
    return (
          <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>svg>
        )
}

function IconUsers({ className }: { className?: string }) {
    return (
          <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
          </svg>svg>
        )
}

function IconBook({ className }: { className?: string }) {
    return (
          <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
          </svg>svg>
        )
}

function IconCog({ className }: { className?: string }) {
    return (
          <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>svg>
        )
}

// ── Nav config ───────────────────────────────────────────────────────

const NAV = [
  { href: '/',               label: 'Dashboard',      Icon: IconDashboard },
  { href: '/conversations',  label: 'Conversaciones', Icon: IconChat      },
  { href: '/leads',          label: 'Leads',          Icon: IconUsers     },
  { href: '/knowledge',      label: 'Conocimiento',   Icon: IconBook      },
  { href: '/settings',       label: 'Configuración',  Icon: IconCog       },
  ]

// ── Sidebar ──────────────────────────────────────────────────────────

export default function Sidebar() {
    const pathname = usePathname()

  return (
        <aside className="hidden md:flex flex-col w-60 border-r border-gray-800/60 bg-gray-950 sticky top-0 h-screen">
          {/* Logo */}
              <div className="flex items-center gap-2.5 px-5 h-16 border-b border-gray-800/60">
                      <div className="w-7 h-7 rounded-lg bg-green-500 flex items-center justify-center text-black font-bold text-sm">
                                A
                      </div>div>
                      <div>
                                <p className="text-sm font-semibold text-white leading-tight">Agentic</p>p>
                                <p className="text-xs text-gray-500 leading-tight">Sales Suite</p>p>
                      </div>div>
              </div>div>
        
          {/* Nav */}
              <nav className="flex-1 px-3 py-4 space-y-0.5">
                {NAV.map(({ href, label, Icon }) => {
                    const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
                                return (
                                              <Link
                                                              key={href}
                                                              href={href}
                                                              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors group ${
                                                                                active
                                                                                  ? 'bg-gray-800 text-white'
                                                                                  : 'text-gray-400 hover:text-white hover:bg-gray-800/60'
                                                              }`}
                                                            >
                                                            <Icon
                                                                              className={`w-4 h-4 shrink-0 transition-opacity ${
                                                                                                  active ? 'opacity-100' : 'opacity-50 group-hover:opacity-100'
                                                                              }`}
                                                                            />
                                                {label}
                                              </Link>Link>
                                            )
                })}
              </nav>nav>
        
          {/* Footer */}
              <div className="px-5 py-4 border-t border-gray-800/60">
                      <div className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                                <span className="text-xs text-gray-500">API conectada</span>span>
                      </div>div>
              </div>div>
        </aside>aside>
      )
}</aside>
