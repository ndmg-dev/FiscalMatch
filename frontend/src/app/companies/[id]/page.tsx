"use client"

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, FileText, Code, Zap, Calendar, AlertCircle, ChevronLeft, ChevronRight, X } from 'react-feather'

export default function CompanyDetailsPage() {
  const { id } = useParams()
  const router = useRouter()
  const [company, setCompany] = useState<any>(null)

  // Automation Form states
  const [periodo, setPeriodo] = useState('')
  const [spedFile, setSpedFile] = useState<File | null>(null)
  const [xmlFilesMain, setXmlFilesMain] = useState<FileList | null>(null)
  const [syncSieg, setSyncSieg] = useState(false)
  
  // UI states
  const [processingState, setProcessingState] = useState<'idle' | 'uploading_sped' | 'uploading_xml' | 'syncing_sieg_and_reconciling'>('idle')
  const [logs, setLogs] = useState<{message: string, status: 'loading' | 'done' | 'error'}[]>([])
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState<'info' | 'error'>('info')
  // Calendar states
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)

  const daysInMonth = (year: number, month: number) => new Date(year, month + 1, 0).getDate()
  const firstDayOfMonth = (year: number, month: number) => new Date(year, month, 1).getDay()

  const handleDateSelect = (day: number) => {
    const d = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day)
    setSelectedDate(d)
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    setPeriodo(`${yyyy}-${mm}`)
    setIsCalendarOpen(false)
  }

  const renderCalendarDays = () => {
    const year = currentMonth.getFullYear()
    const month = currentMonth.getMonth()
    const daysCount = daysInMonth(year, month)
    const firstDay = firstDayOfMonth(year, month)
    const days = []

    for (let i = 0; i < firstDay; i++) {
      days.push(<div key={`empty-${i}`} className="w-8 h-8" />)
    }

    for (let d = 1; d <= daysCount; d++) {
      const isSelected = selectedDate?.getDate() === d && selectedDate?.getMonth() === month && selectedDate?.getFullYear() === year
      days.push(
        <button
          type="button"
          key={d}
          onClick={() => handleDateSelect(d)}
          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm transition-colors ${
            isSelected 
              ? 'bg-[var(--gold)] text-black font-bold' 
              : 'text-[var(--foreground)] hover:bg-white/10'
          }`}
          data-testid={`day-${d}`}
        >
          {d}
        </button>
      )
    }
    return days
  }


  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}`)
      .then(res => res.json())
      .then(data => setCompany(data))
  }, [id])

  async function handleAutomatedFlow(e: React.FormEvent) {
    e.preventDefault()
    if (!spedFile || !periodo) return

    setMessageType('info')
    setLogs([{ message: 'Enviando arquivo SPED...', status: 'loading' }])
    setProcessingState('uploading_sped')
    
    const formDataSped = new FormData()
    formDataSped.append('periodo', periodo)
    formDataSped.append('file', spedFile)

    try {
      const spedRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}/sped/upload`, {
        method: 'POST',
        body: formDataSped,
      })
      if (!spedRes.ok) throw new Error('Erro ao fazer upload do SPED')
      
      setLogs(prev => [
        { message: 'Arquivo SPED processado com sucesso.', status: 'done' },
      ])

      if (xmlFilesMain && xmlFilesMain.length > 0) {
        setLogs(prev => [...prev, { message: 'Enviando arquivos XML em lote...', status: 'loading' }])
        setProcessingState('uploading_xml')
        const formDataXml = new FormData()
        for (let i = 0; i < xmlFilesMain.length; i++) {
          formDataXml.append('files', xmlFilesMain[i])
        }
        const xmlRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}/xml/upload`, {
          method: 'POST',
          body: formDataXml,
        })
        if (!xmlRes.ok) throw new Error('Erro ao fazer upload dos XMLs')
        
        setLogs(prev => [
          ...prev.slice(0, -1),
          { message: `${xmlFilesMain.length} arquivos XML processados com sucesso.`, status: 'done' },
        ])
      }

      setProcessingState('syncing_sieg_and_reconciling')
      setLogs(prev => [...prev, { message: syncSieg ? 'Consultando notas na SIEG e conciliando dados...' : 'Iniciando conciliação de dados...', status: 'loading' }])
      
      const reconRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/conciliacoes?empresa_id=${id}&periodo=${periodo}&sync_sieg=${syncSieg}`,
        { method: 'POST' }
      )
      
      if (!reconRes.ok) {
        const err = await reconRes.json()
        throw new Error(err.detail || 'Erro na conciliação')
      }
      
      const data = await reconRes.json()

      setLogs(prev => [
        ...prev.slice(0, -1),
        { message: 'Conciliação concluída com sucesso!', status: 'done' }
      ])
      
      await new Promise(r => setTimeout(r, 1200))

      if (data.warning) {
        router.push(`/reconciliations/${id}/${periodo}?warning=${encodeURIComponent(data.warning)}`)
      } else {
        router.push(`/reconciliations/${id}/${periodo}`)
      }

    } catch (err: any) {
      setLogs(prev => {
        const newLogs = [...prev]
        if (newLogs.length > 0) newLogs[newLogs.length - 1].status = 'error'
        newLogs.push({ message: err.message, status: 'error' })
        return newLogs
      })
      setMessageType('error')
      setMessage(err.message)
      setProcessingState('idle')
    }
  }


  if (!company) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-[var(--foreground-muted)]">Carregando...</div>
      </div>
    )
  }

  const isProcessing = processingState !== 'idle'

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/companies" className="text-[var(--foreground-muted)] hover:text-[var(--gold)] transition-colors">
          <ArrowLeft size={22} />
        </Link>
        <div>
          <h1 className="page-title">
            <FileText />
            {company.razao_social}
          </h1>
          <p className="text-sm text-[var(--foreground-muted)] mt-1 ml-10">CNPJ: {company.cnpj}</p>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={messageType === 'error' ? 'alert-error' : 'alert-info'}>
          <div className="flex items-center gap-2">
            {messageType === 'error' ? <AlertCircle size={16} /> : <Zap size={16} className="animate-pulse" />}
            {message}
          </div>
        </div>
      )}

      {/* Primary Action: Automated Flow */}
      <div className="glass-card rounded-2xl p-8 gold-accent relative">
        {/* Loading overlay effect */}
        {isProcessing && (
          <div className="absolute inset-0 rounded-2xl bg-black/80 backdrop-blur-md z-10 flex flex-col items-center justify-center p-8">
             <div className="bg-[var(--background-card)] border border-[var(--gold-border)] rounded-2xl p-6 w-full max-w-md shadow-2xl">
               <h3 className="text-xl font-bold text-[var(--gold)] mb-6 flex items-center gap-2">
                 <Zap size={24} className="animate-pulse" /> Processando Conciliação
               </h3>
               <div className="space-y-4">
                 {logs.map((log, i) => (
                   <div key={i} className="flex items-center gap-3">
                     {log.status === 'loading' && <div className="w-5 h-5 rounded-full border-2 border-[var(--gold)] border-t-transparent animate-spin shrink-0"></div>}
                     {log.status === 'done' && <div className="w-5 h-5 rounded-full bg-[var(--gold)] flex items-center justify-center shrink-0"><span className="text-black text-xs font-bold">✓</span></div>}
                     {log.status === 'error' && <AlertCircle size={20} className="text-red-400 shrink-0" />}
                     <span className={`text-sm ${log.status === 'loading' ? 'text-[var(--foreground)] font-medium animate-pulse' : 'text-[var(--foreground-muted)]'}`}>
                       {log.message}
                     </span>
                   </div>
                 ))}
               </div>
             </div>
          </div>
        )}

        <div className="flex items-center gap-4 mb-8">
          <div className="w-12 h-12 rounded-xl bg-[var(--gold-glow)] border border-[var(--gold-border)] flex items-center justify-center">
            <Zap size={22} className="text-[var(--gold)]" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-[var(--foreground)]">Conciliação Automática</h2>
            <p className="text-[var(--foreground-muted)] mt-1">
              Envie o SPED e o sistema fará a busca no SIEG automaticamente.
            </p>
          </div>
        </div>

        <form onSubmit={handleAutomatedFlow} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">
                <Calendar size={13} className="inline mr-1 mb-0.5" />
                Período (YYYY-MM)
              </label>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setIsCalendarOpen(true)}
                  className="input-field w-full text-left flex items-center justify-between"
                  disabled={isProcessing}
                  data-testid="open-calendar-btn"
                >
                  <span className={periodo ? 'text-[var(--foreground)]' : 'text-[var(--foreground-muted)]'}>
                    {periodo ? periodo : 'Selecione uma data (YYYY-MM)'}
                  </span>
                  <Calendar size={16} className="text-[var(--foreground-muted)]" />
                </button>
                {isCalendarOpen && (
                  <div className="absolute z-50 mt-2 p-4 bg-[#1e1e1e] border border-[var(--gold-border)] rounded-2xl shadow-xl w-[300px]" data-testid="calendar-modal">
                    <div className="flex justify-between items-center mb-4">
                      <button type="button" onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1))} className="p-1 hover:bg-white/5 rounded">
                        <ChevronLeft size={20} className="text-[var(--foreground-muted)]" />
                      </button>
                      <div className="font-semibold text-[var(--foreground)]">
                        {currentMonth.toLocaleString('pt-BR', { month: 'long', year: 'numeric' })}
                      </div>
                      <button type="button" onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1))} className="p-1 hover:bg-white/5 rounded">
                        <ChevronRight size={20} className="text-[var(--foreground-muted)]" />
                      </button>
                    </div>
                    <div className="grid grid-cols-7 gap-1 text-center mb-2">
                      {['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map(d => (
                        <div key={d} className="text-xs text-[var(--foreground-muted)] font-medium">{d}</div>
                      ))}
                    </div>
                    <div className="grid grid-cols-7 gap-1 place-items-center">
                      {renderCalendarDays()}
                    </div>
                    <div className="mt-4 pt-3 border-t border-white/10 text-right">
                      <button type="button" onClick={() => setIsCalendarOpen(false)} className="text-xs text-[var(--foreground-muted)] hover:text-white" data-testid="close-calendar-btn">
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">
                Arquivo SPED (.txt)
              </label>
              <input
                type="file"
                accept=".txt"
                onChange={e => setSpedFile(e.target.files?.[0] || null)}
                className="file-input"
                required
                disabled={isProcessing}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">
                <Code size={13} className="inline mr-1 mb-0.5" />
                Arquivos XML Opcionais (Em lote)
              </label>
              <input
                type="file"
                accept=".xml"
                multiple
                onChange={e => setXmlFilesMain(e.target.files)}
                className="file-input w-full"
                disabled={isProcessing}
              />
              <p className="text-xs text-[var(--foreground-muted)] mt-1">
                Selecione as notas para cruzar manualmente junto com o SPED.
              </p>
            </div>
            <div className="flex flex-col justify-center">
              <label className="flex items-center gap-3 cursor-pointer mt-6">
                <input
                  type="checkbox"
                  checked={syncSieg}
                  onChange={e => setSyncSieg(e.target.checked)}
                  className="w-5 h-5 rounded border-white/20 bg-black/50 text-[var(--gold)] focus:ring-[var(--gold)] focus:ring-offset-0"
                  disabled={isProcessing}
                />
                <span className="text-sm font-medium text-[var(--foreground)]">
                  Consultar API da SIEG Automaticamente
                </span>
              </label>
              <p className="text-xs text-[var(--foreground-muted)] mt-1 ml-8">
                Desmarque se a API estiver fora do ar ou se você já subiu todos os XMLs necessários.
              </p>
            </div>
          </div>

          <button 
            disabled={isProcessing || !spedFile || !periodo} 
            className="btn-gold w-full py-4 rounded-xl text-lg font-bold flex items-center justify-center gap-2"
          >
            <Zap size={20} />
            {isProcessing ? 'Processando...' : (syncSieg ? 'Processar e Conciliar com SIEG' : 'Processar Arquivos Localmente')}
          </button>
        </form>
      </div>

    </div>
  )
}
