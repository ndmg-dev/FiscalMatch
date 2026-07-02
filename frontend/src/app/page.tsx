'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Briefcase, FileText, Database, CheckCircle, AlertTriangle, XCircle, ArrowRight, Activity, TrendingUp, Clock } from 'react-feather'

interface DashboardData {
  total_empresas: number
  total_xmls: number
  total_sped_docs: number
  total_conciliacoes: number
  compliance_rate: number
  status_breakdown: {
    OK: number
    FALTANTE: number
    DIVERGENTE: number
    NAO_ATRIBUIDA: number
    IGNORADA_POR_REGRA: number
  }
  recent_reconciliations: {
    empresa_id: string
    empresa_nome: string
    periodo: string
    total: number
    ok: number
    faltante: number
    divergente: number
    last_run: string | null
  }[]
  empresas: {
    id: string
    razao_social: string
    cnpj: string
    xml_count: number
    sped_count: number
  }[]
}

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/dashboard/stats`)
      .then(res => res.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const formatCNPJ = (cnpj: string) => {
    return cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')
  }

  const timeAgo = (dateStr: string | null) => {
    if (!dateStr) return '-'
    const d = dateStr.includes('T') && !dateStr.endsWith('Z') && !dateStr.includes('+') ? `${dateStr}Z` : dateStr
    let diff = Date.now() - new Date(d).getTime()
    if (diff < 0) diff = 0
    const mins = Math.floor(diff / 60000)
    if (mins === 0) return 'agora'
    if (mins < 60) return `${mins}min atrás`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h atrás`
    const days = Math.floor(hours / 24)
    return `${days}d atrás`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-[var(--foreground-muted)] animate-pulse text-lg">Carregando Dashboard...</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-red-400">Erro ao carregar dados do dashboard.</div>
      </div>
    )
  }

  const totalActionable = data.status_breakdown.OK + data.status_breakdown.FALTANTE + data.status_breakdown.DIVERGENTE + data.status_breakdown.NAO_ATRIBUIDA

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--foreground)] tracking-tight">Dashboard</h1>
          <p className="text-[var(--foreground-muted)] text-sm mt-1">Visão geral do sistema fiscal</p>
        </div>
        <Link href="/companies/new" className="btn-gold px-5 py-2.5 rounded-xl text-sm font-semibold inline-flex items-center gap-2">
          <Briefcase size={16} />
          Nova Empresa
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card rounded-2xl p-5 group">
          <div className="flex items-center justify-between mb-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-[var(--gold-glow)] border border-[var(--gold-border)]">
              <Briefcase size={18} className="text-[var(--gold)]" />
            </div>
            <span className="text-xs text-[var(--foreground-muted)] uppercase tracking-wider">Empresas</span>
          </div>
          <div className="text-3xl font-bold text-[var(--foreground)]">{data.total_empresas}</div>
          <p className="text-xs text-[var(--foreground-muted)] mt-1">cadastradas no sistema</p>
        </div>

        <div className="glass-card rounded-2xl p-5 group">
          <div className="flex items-center justify-between mb-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-[var(--gold-glow)] border border-[var(--gold-border)]">
              <FileText size={18} className="text-[var(--gold)]" />
            </div>
            <span className="text-xs text-[var(--foreground-muted)] uppercase tracking-wider">XMLs</span>
          </div>
          <div className="text-3xl font-bold text-[var(--foreground)]">{data.total_xmls.toLocaleString('pt-BR')}</div>
          <p className="text-xs text-[var(--foreground-muted)] mt-1">documentos importados</p>
        </div>

        <div className="glass-card rounded-2xl p-5 group">
          <div className="flex items-center justify-between mb-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-[var(--gold-glow)] border border-[var(--gold-border)]">
              <Database size={18} className="text-[var(--gold)]" />
            </div>
            <span className="text-xs text-[var(--foreground-muted)] uppercase tracking-wider">SPED</span>
          </div>
          <div className="text-3xl font-bold text-[var(--foreground)]">{data.total_sped_docs.toLocaleString('pt-BR')}</div>
          <p className="text-xs text-[var(--foreground-muted)] mt-1">registros fiscais</p>
        </div>

        <div className="glass-card rounded-2xl p-5 group">
          <div className="flex items-center justify-between mb-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-[var(--gold-glow)] border border-[var(--gold-border)]">
              <Activity size={18} className="text-[var(--gold)]" />
            </div>
            <span className="text-xs text-[var(--foreground-muted)] uppercase tracking-wider">Conciliações</span>
          </div>
          <div className="text-3xl font-bold text-[var(--foreground)]">{data.total_conciliacoes.toLocaleString('pt-BR')}</div>
          <p className="text-xs text-[var(--foreground-muted)] mt-1">cruzamentos realizados</p>
        </div>
      </div>

      {/* Compliance + Status Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Compliance Gauge */}
        <div className="glass-card rounded-2xl p-6 flex flex-col items-center justify-center">
          <TrendingUp size={20} className="text-[var(--gold)] mb-3" />
          <h3 className="text-sm font-medium text-[var(--foreground-muted)] mb-4">Taxa de Conformidade</h3>
          <div className="relative w-36 h-36 flex items-center justify-center">
            <svg className="w-36 h-36 transform -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(201,168,76,0.1)" strokeWidth="10" />
              <circle
                cx="60" cy="60" r="52" fill="none"
                stroke="url(#goldGradient)" strokeWidth="10"
                strokeLinecap="round"
                strokeDasharray={`${(data.compliance_rate / 100) * 327} 327`}
                className="transition-all duration-1000 ease-out"
              />
              <defs>
                <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#c9a84c" />
                  <stop offset="100%" stopColor="#d4b85c" />
                </linearGradient>
              </defs>
            </svg>
            <span className="absolute text-3xl font-bold text-[var(--gold)]">
              {data.compliance_rate}%
            </span>
          </div>
          <p className="text-xs text-[var(--foreground-muted)] mt-4 text-center">
            {data.status_breakdown.OK} de {totalActionable} notas conciliadas com sucesso
          </p>
        </div>

        {/* Status Breakdown */}
        <div className="glass-card rounded-2xl p-6 lg:col-span-2">
          <h3 className="text-sm font-medium text-[var(--foreground-muted)] mb-5 flex items-center gap-2">
            <Activity size={16} className="text-[var(--gold)]" />
            Distribuição por Status
          </h3>
          <div className="space-y-4">
            {[
              { label: 'Conciliado (OK)', value: data.status_breakdown.OK, color: 'bg-emerald-500', textColor: 'text-emerald-400' },
              { label: 'Faltante', value: data.status_breakdown.FALTANTE, color: 'bg-red-500', textColor: 'text-red-400' },
              { label: 'Divergente', value: data.status_breakdown.DIVERGENTE, color: 'bg-amber-500', textColor: 'text-amber-400' },
              { label: 'Não Atribuída', value: data.status_breakdown.NAO_ATRIBUIDA, color: 'bg-blue-500', textColor: 'text-blue-400' },
              { label: 'Ignorada por Regra', value: data.status_breakdown.IGNORADA_POR_REGRA, color: 'bg-gray-500', textColor: 'text-gray-400' },
            ].map(item => {
              const pct = data.total_conciliacoes > 0 ? (item.value / data.total_conciliacoes) * 100 : 0
              return (
                <div key={item.label} className="group">
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <span className={`font-medium ${item.textColor}`}>{item.label}</span>
                    <span className="text-[var(--foreground-muted)]">{item.value.toLocaleString('pt-BR')} <span className="text-xs">({pct.toFixed(1)}%)</span></span>
                  </div>
                  <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${item.color} transition-all duration-700 ease-out`}
                      style={{ width: `${Math.max(pct, 0.5)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Two columns: Recent + Companies */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Reconciliations */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-medium text-[var(--foreground-muted)] flex items-center gap-2">
              <Clock size={16} className="text-[var(--gold)]" />
              Conciliações Recentes
            </h3>
          </div>
          {data.recent_reconciliations.length === 0 ? (
            <div className="text-center py-8 text-[var(--foreground-muted)] text-sm">
              Nenhuma conciliação realizada ainda.
            </div>
          ) : (
            <div className="space-y-3">
              {data.recent_reconciliations.map((r, i) => (
                <Link
                  key={i}
                  href={`/reconciliations/${r.empresa_id}/${r.periodo}`}
                  className="block p-4 rounded-xl border border-[var(--card-border)] hover:border-[var(--gold-border)] hover:bg-[var(--gold-glow)] transition-all group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--gold)] transition-colors truncate max-w-[220px]">{r.empresa_nome}</p>
                      <p className="text-xs text-[var(--foreground-muted)] mt-0.5">Período: {r.periodo}</p>
                    </div>
                    <span className="text-xs text-[var(--foreground-muted)] whitespace-nowrap">{timeAgo(r.last_run)}</span>
                  </div>
                  <div className="flex gap-3 text-xs">
                    <span className="flex items-center gap-1 text-emerald-400">
                      <CheckCircle size={12} /> {r.ok.toLocaleString('pt-BR')}
                    </span>
                    <span className="flex items-center gap-1 text-red-400">
                      <XCircle size={12} /> {r.faltante.toLocaleString('pt-BR')}
                    </span>
                    <span className="flex items-center gap-1 text-amber-400">
                      <AlertTriangle size={12} /> {r.divergente.toLocaleString('pt-BR')}
                    </span>
                    <span className="text-[var(--foreground-muted)] ml-auto">{r.total.toLocaleString('pt-BR')} total</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Companies */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-medium text-[var(--foreground-muted)] flex items-center gap-2">
              <Briefcase size={16} className="text-[var(--gold)]" />
              Empresas Cadastradas
            </h3>
            <Link href="/companies" className="text-xs text-[var(--gold)] hover:text-[var(--gold-light)] inline-flex items-center gap-1 transition-colors">
              Ver todas <ArrowRight size={12} />
            </Link>
          </div>
          {data.empresas.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-[var(--foreground-muted)] text-sm mb-4">Nenhuma empresa cadastrada.</p>
              <Link href="/companies/new" className="btn-gold px-4 py-2 rounded-lg text-sm font-semibold">
                Cadastrar Empresa
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {data.empresas.map(e => (
                <Link
                  key={e.id}
                  href={`/companies/${e.id}`}
                  className="flex items-center justify-between p-4 rounded-xl border border-[var(--card-border)] hover:border-[var(--gold-border)] hover:bg-[var(--gold-glow)] transition-all group"
                >
                  <div>
                    <p className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--gold)] transition-colors">{e.razao_social}</p>
                    <p className="text-xs text-[var(--foreground-muted)] mt-0.5 font-mono">{formatCNPJ(e.cnpj)}</p>
                  </div>
                  <div className="flex gap-4 text-xs text-[var(--foreground-muted)]">
                    <span title="XMLs importados" className="flex items-center gap-1">
                      <FileText size={12} /> {e.xml_count.toLocaleString('pt-BR')}
                    </span>
                    <span title="Registros SPED" className="flex items-center gap-1">
                      <Database size={12} /> {e.sped_count.toLocaleString('pt-BR')}
                    </span>
                    <ArrowRight size={14} className="text-[var(--gold)] opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
