"use client"

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Briefcase, Plus, ChevronRight, Inbox } from 'react-feather'

export default function CompaniesPage() {
  const [companies, setCompanies] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/`)
      .then(res => res.json())
      .then(data => {
        setCompanies(data)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="page-title">
          <Briefcase />
          Empresas
        </h1>
        <Link
          href="/companies/new"
          className="btn-gold px-5 py-2.5 rounded-lg text-sm inline-flex items-center gap-2"
        >
          <Plus size={16} />
          Nova Empresa
        </Link>
      </div>

      <div className="glass-card rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-[var(--foreground-muted)]">Carregando...</div>
        ) : companies.length === 0 ? (
          <div className="p-16 text-center flex flex-col items-center">
            <div className="h-16 w-16 rounded-full flex items-center justify-center mb-4 bg-[var(--gold-glow)] border border-[var(--gold-border)]">
              <Inbox size={28} className="text-[var(--gold)]" />
            </div>
            <p className="text-lg text-[var(--foreground)] mb-2">Nenhuma empresa cadastrada</p>
            <p className="text-sm text-[var(--foreground-muted)]">Cadastre a primeira empresa para iniciar a conciliação.</p>
          </div>
        ) : (
          <table className="min-w-full">
            <thead className="table-header">
              <tr>
                <th className="text-left">CNPJ</th>
                <th className="text-left">Razão Social</th>
                <th className="text-left">Ações</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((company: any) => (
                <tr key={company.id} className="table-row">
                  <td className="font-mono text-sm">{company.cnpj}</td>
                  <td>{company.razao_social}</td>
                  <td>
                    <Link
                      href={`/companies/${company.id}`}
                      className="text-[var(--gold)] hover:text-[var(--gold-light)] flex items-center gap-1 text-sm font-medium transition-colors"
                    >
                      Acessar
                      <ChevronRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
