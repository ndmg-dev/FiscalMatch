"use client"

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Briefcase, GitMerge, Upload, Settings } from 'react-feather'

const navItems = [
  { href: '/', label: 'Dashboard', icon: Home },
  { href: '/companies', label: 'Empresas', icon: Briefcase },
  { href: '/companies/new', label: 'Nova Empresa', icon: Upload },
]

export function Sidebar() {
  const pathname = usePathname()

  function isActive(href: string) {
    if (href === '/') return pathname === '/'
    // Exact match takes priority
    if (pathname === href) return true
    // Only highlight as active if no other nav item is a more specific match
    if (pathname.startsWith(href + '/')) {
      const hasMoreSpecific = navItems.some(
        item => item.href !== href && item.href.startsWith(href) && pathname.startsWith(item.href)
      )
      return !hasMoreSpecific
    }
    return false
  }

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo relative flex justify-center py-6">
        {/* Subtle glow behind logo */}
        <div className="absolute inset-0 bg-gradient-to-b from-[var(--gold-glow)] to-transparent opacity-30 pointer-events-none"></div>
        <Link href="/" className="relative flex items-center justify-center group w-full px-2 z-10">
          <img 
            src="/logo-full.png" 
            alt="Mendonça Galvão" 
            className="w-full max-w-[200px] h-auto object-contain opacity-90 group-hover:opacity-100 transition-all duration-500 hover:scale-105"
            style={{ mixBlendMode: 'screen' }}
          />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <span className="text-[10px] uppercase tracking-widest text-[var(--foreground-muted)] px-4 mb-2 mt-2">
          Menu
        </span>
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${active ? 'active' : ''}`}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="flex items-center gap-2">
          <Settings size={13} />
          <span>FiscalMatch v0.1 — Pre-MVP</span>
        </div>
      </div>
    </aside>
  )
}
