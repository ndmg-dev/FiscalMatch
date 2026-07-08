"use client"

import React, { useState, useEffect } from 'react'
import { useSearchParams, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, FileText, Download, AlertTriangle, ChevronDown, ChevronRight } from 'react-feather'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

export default function ReconciliationReportPage() {
  const { empresa_id, periodo } = useParams()
  const searchParams = useSearchParams()
  const warning = searchParams.get('warning')

  const [report, setReport] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [statusFilter, setStatusFilter] = useState<string>('ALL')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/conciliacoes/${empresa_id}/${periodo}/relatorio?limit=1000&status=${statusFilter}`).then(res => {
        if (!res.ok) throw new Error(`Erro ${res.status}`);
        return res.json();
      }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/conciliacoes/${empresa_id}/historico`).then(res => {
        if (!res.ok) throw new Error(`Erro ${res.status}`);
        return res.json();
      })
    ]).then(([reportData, historyData]) => {
      setReport(reportData)
      if (Array.isArray(historyData)) {
        const periodStats = historyData.find(h => h.periodo === periodo)
        if (periodStats) setStats(periodStats)
      }
      setLoading(false)
    }).catch(err => {
      console.error(err);
      setLoading(false);
    })
  }, [empresa_id, periodo, statusFilter])

  const toggleRow = (id: string) => {
    const next = new Set(expandedRows)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setExpandedRows(next)
  }

  const formatBRL = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }

  const exportPDF = () => {
    const doc = new jsPDF('landscape')
    doc.text(`Relatório de Conciliação - ${periodo}`, 14, 15)
    
    const tableColumn = ["Status", "Chave NF-e", "Série/Num", "Emissão", "Valor XML", "Valor SPED", "Obs"]
    const tableRows = report.map(row => [
      row.status,
      row.chave_nfe || '-',
      `${row.serie || '-'} / ${row.numero || '-'}`,
      row.data_emissao || '-',
      formatBRL(row.valor_xml),
      formatBRL(row.valor_sped),
      row.observacao || ''
    ])

    autoTable(doc, {
      head: [tableColumn],
      body: tableRows,
      startY: 20,
      styles: { fontSize: 8 },
      headStyles: { fillColor: [201, 168, 76] }
    })

    doc.save(`conciliacao_${periodo}.pdf`)
  }

  const statusBadge: Record<string, string> = {
    OK: 'badge-ok',
    FALTANTE: 'badge-missing',
    NAO_ATRIBUIDA: 'badge-unmatched',
    DIVERGENTE: 'badge-divergent',
    IGNORADA_POR_REGRA: 'badge-ignored',
  }

  const uniqueStatuses = ['OK', 'FALTANTE', 'DIVERGENTE', 'IGNORADA_POR_REGRA', 'NAO_ATRIBUIDA']
  const filteredReport = report

  // Use stats from backend if available, otherwise fallback to calculating from loaded records
  const displayStats = stats ? {
    'OK': stats.ok,
    'FALTANTE': stats.faltante,
    'DIVERGENTE': stats.divergente,
    'IGNORADA_POR_REGRA': stats.ignorada || 0,
    'NAO_ATRIBUIDA': stats.nao_atribuida || 0,
    'Total Registros': stats.total
  } : report.reduce((acc, curr) => {
    acc[curr.status] = (acc[curr.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-6">
      {/* Warning Alert */}
      {warning && (
        <div className="alert-error flex items-center gap-3 py-4">
          <AlertTriangle size={24} className="text-red-400 shrink-0" />
          <span className="text-sm font-medium">{warning}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <Link
            href={`/companies/${empresa_id}`}
            className="text-[var(--foreground-muted)] hover:text-[var(--gold)] text-sm inline-flex items-center gap-1 mb-3 transition-colors"
          >
            <ArrowLeft size={14} /> Voltar para a Empresa
          </Link>
          <h1 className="page-title">
            <FileText />
            Relatório de Conciliação
          </h1>
          <p className="text-[var(--foreground-muted)] text-sm ml-10">Período: {periodo}</p>
        </div>
        <div className="flex flex-col gap-3 items-end">
          <div className="flex gap-3">
            <button
              onClick={exportPDF}
              className="btn-gold px-4 py-2 rounded-lg text-sm inline-flex items-center gap-2"
            >
              <FileText size={14} />
              PDF
            </button>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL}/conciliacoes/${empresa_id}/${periodo}/exportar.csv`}
              className="btn-ghost px-4 py-2 rounded-lg text-sm inline-flex items-center gap-2"
            >
              <Download size={14} />
              CSV
            </a>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL}/conciliacoes/${empresa_id}/${periodo}/exportar.xlsx`}
              className="btn-ghost px-4 py-2 rounded-lg text-sm inline-flex items-center gap-2"
            >
              <Download size={14} />
              Excel
            </a>
          </div>
          
          <select 
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input-field text-sm py-2 px-3 w-48 mt-2"
          >
            <option value="ALL">Todos os Status</option>
            {uniqueStatuses.map(s => (
              <option key={s} value={s}>{s === 'FALTANTE' ? 'Faltante no SPED' : s.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Status Summary Scroller */}
      {report.length > 0 && (
        <div className="flex gap-4 overflow-x-auto py-4 px-2 -mx-2 hide-scrollbar snap-x">
          {Object.entries(displayStats).map(([status, count]) => (
            <div 
              key={status} 
              onClick={() => setStatusFilter(statusFilter === status ? 'ALL' : status)}
              className={`min-w-[200px] p-5 rounded-2xl flex-shrink-0 snap-start border cursor-pointer transition-all shadow-lg backdrop-blur-md ${statusFilter === status ? 'border-[var(--gold)] bg-[var(--gold-glow)] shadow-[0_0_15px_rgba(201,168,76,0.3)]' : 'bg-black/60 border-[var(--card-border)] hover:border-[var(--gold-border)] hover:bg-[var(--card-bg)] hover:-translate-y-1'}`}
            >
              <h3 className="text-[var(--foreground-muted)] text-sm font-medium mb-3">{status === 'FALTANTE' ? 'Faltante no SPED' : status.replace(/_/g, ' ')}</h3>
              <div className="flex items-center justify-between gap-3">
                <span className="text-3xl font-bold text-[var(--gold)] truncate" title={String(count)}>
                  {Number(count).toLocaleString('pt-BR')}
                </span>
                <span className={`badge whitespace-nowrap ${statusBadge[status] || 'badge-ignored'}`}>{status === 'FALTANTE' ? 'Faltante no SPED' : status}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Warning banner for large datasets */}
      {report.length >= 1000 && (
        <div className="alert-info text-sm py-2">
          Exibindo os primeiros 1000 registros para não travar o navegador. Use os botões de exportação acima para visualizar o relatório completo.
        </div>
      )}

      {/* Table */}
      <div className="glass-card rounded-xl overflow-hidden overflow-x-auto">
        {loading ? (
          <div className="p-12 text-center text-[var(--foreground-muted)]">Carregando relatório...</div>
        ) : filteredReport.length === 0 ? (
          <div className="p-12 text-center text-[var(--foreground-muted)]">
            Nenhum registro encontrado para este filtro.
          </div>
        ) : (
          <table className="min-w-full text-left whitespace-nowrap">
            <thead className="table-header">
              <tr>
                <th>Status</th>
                <th>Chave NF-e</th>
                <th>Série / Número</th>
                <th>Emissão</th>
                <th className="text-right">Valor XML</th>
                <th className="text-right">Valor SPED</th>
                <th>Diferença / Obs</th>
              </tr>
            </thead>
            <tbody>
              {filteredReport.map((row: any) => (
                <React.Fragment key={row.id}>
                  <tr 
                    className="table-row cursor-pointer hover:bg-[var(--gold-glow)] transition-colors"
                    onClick={() => toggleRow(row.id)}
                  >
                    <td>
                      <div className="flex items-center gap-2">
                        {expandedRows.has(row.id) ? <ChevronDown size={14} className="text-[var(--gold)]" /> : <ChevronRight size={14} className="text-[var(--foreground-muted)]" />}
                        <span className={`badge ${statusBadge[row.status] || 'badge-ignored'}`}>
                          {row.status === 'FALTANTE' ? 'Faltante no SPED' : row.status}
                        </span>
                      </div>
                    </td>
                    <td className="font-mono text-xs text-[var(--foreground-muted)]">
                      {row.chave_nfe || '-'}
                    </td>
                    <td>
                      {row.serie || '-'} / {row.numero || '-'}
                    </td>
                    <td>{row.data_emissao || '-'}</td>
                    <td className="text-right font-medium">
                      {formatBRL(row.valor_xml)}
                    </td>
                    <td className="text-right font-medium">
                      {formatBRL(row.valor_sped)}
                    </td>
                    <td className="text-xs text-[var(--foreground-muted)]">
                      {row.observacao}
                    </td>
                  </tr>
                  {expandedRows.has(row.id) && (
                    <tr className="bg-[var(--background-subtle)] border-b border-[var(--card-border)]">
                      <td colSpan={7} className="p-6 px-12">
                        <div className="grid grid-cols-2 gap-8 text-sm">
                          <div className="bg-black/40 p-5 rounded-xl border border-[var(--card-border)] shadow-inner">
                            <h4 className="font-bold text-[var(--gold)] mb-4 flex items-center gap-2 border-b border-[var(--card-border)] pb-2">
                              Dados do SPED
                            </h4>
                            <div className="space-y-3 text-[var(--foreground-muted)]">
                              <p><strong className="text-[var(--foreground)]">CNPJ Participante:</strong> {row.cnpj_emitente || '-'}</p>
                              <p><strong className="text-[var(--foreground)]">Nome Participante:</strong> {row.nome_participante || '-'}</p>
                              <p><strong className="text-[var(--foreground)]">Data Entrada/Saída:</strong> {row.data_entrada_saida || '-'}</p>
                              <p><strong className="text-[var(--foreground)]">Cod. Situação:</strong> {row.origem_documento === 'SPED' ? row.situacao_nota : '-'}</p>
                            </div>
                          </div>
                          <div className="bg-black/40 p-5 rounded-xl border border-[var(--card-border)] shadow-inner">
                            <h4 className="font-bold text-[var(--gold)] mb-4 flex items-center gap-2 border-b border-[var(--card-border)] pb-2">
                              Dados do XML
                            </h4>
                            <div className="space-y-3 text-[var(--foreground-muted)]">
                              <p><strong className="text-[var(--foreground)]">CNPJ Emitente:</strong> {row.cnpj_emitente || '-'}</p>
                              <p><strong className="text-[var(--foreground)]">CNPJ Destinatário:</strong> {row.cnpj_destinatario || '-'}</p>
                              <p><strong className="text-[var(--foreground)]">Origem:</strong> {row.origem_documento || '-'}</p>
                              <p><strong className="text-[var(--foreground)]">Situação SEFAZ:</strong> {row.origem_documento !== 'SPED' ? row.situacao_nota : '-'}</p>
                            </div>
                          </div>
                        </div>
                        {row.diferenca && (
                          <div className="mt-6 bg-[var(--gold-glow)] p-4 rounded-xl border border-[var(--gold-border)] text-sm shadow-md">
                            <strong className="text-[var(--gold-light)] block mb-2 font-bold text-base">Diferenças Detectadas na Conciliação:</strong>
                            <pre className="text-xs text-[var(--foreground)] font-mono whitespace-pre-wrap">{JSON.stringify(row.diferenca, null, 2)}</pre>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
