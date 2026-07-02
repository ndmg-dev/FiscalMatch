import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Sidebar } from './components/Sidebar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'FiscalMatch — Reconciliação Fiscal',
  description: 'Reconciliação inteligente de documentos fiscais XML contra registros SPED Fiscal.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className={`${inter.className}`} suppressHydrationWarning>
        <div className="bg-blobs">
          <div className="blob blob-1"></div>
          <div className="blob blob-2"></div>
          <div className="blob blob-3"></div>
        </div>
        <Sidebar />
        <main className="main-content animate-fade-in">
          {children}
        </main>
      </body>
    </html>
  )
}
