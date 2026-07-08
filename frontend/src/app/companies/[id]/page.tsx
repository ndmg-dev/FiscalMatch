"use client"

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, FileText, Code, Zap, Calendar, AlertCircle, ChevronLeft, ChevronRight } from 'react-feather'

export default function CompanyDetailsPage() {
  const { id } = useParams()
  const router = useRouter()
  const [company, setCompany] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [isDeleting, setIsDeleting] = useState(false)
  
  // Tabs: 'conciliacao' | 'base_dados' | 'auditoria'
  const [activeTab, setActiveTab] = useState<'conciliacao' | 'base_dados' | 'auditoria'>('conciliacao')

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
  
  // Base de Dados states
  const [xmlSummary, setXmlSummary] = useState<any[]>([])
  const [xmlList, setXmlList] = useState<any[]>([])
  const [selectedXmlMonth, setSelectedXmlMonth] = useState<string | null>(null)
  const [loadingXmls, setLoadingXmls] = useState(false)

  const fetchXmlsForMonth = async (mes: string | null) => {
    setSelectedXmlMonth(mes)
    setLoadingXmls(true)
    try {
      const url = mes 
        ? `${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}/xml/list?mes=${mes}`
        : `${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}/xml/list`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const data = await res.json()
      setXmlList(data)
    } catch (err) {
      console.error("Erro ao buscar xmls", err)
    } finally {
      setLoadingXmls(false)
    }
  }
  
  // Auditoria states
  const [auditPeriod, setAuditPeriod] = useState('')
  const [auditReport, setAuditReport] = useState<any>(null)

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
      .then(res => {
        if (!res.ok) throw new Error(`Erro ${res.status}`);
        return res.json();
      })
      .then(data => setCompany(data))
      .catch(err => console.error("Erro ao buscar empresa:", err))
      
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/conciliacoes/${id}/historico`)
      .then(res => {
        if (!res.ok) throw new Error(`Erro ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (Array.isArray(data)) {
          setHistory(data)
        }
      })
      .catch(err => console.error("Erro ao buscar histórico:", err))
      
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}/xml/summary`)
      .then(res => {
        if (!res.ok) throw new Error(`Erro ${res.status}`);
        return res.json();
      })
      .then(data => {
        setXmlSummary(data)
        fetchXmlsForMonth(null) // Load all XMLs initially
      })
      .catch(err => console.error("Erro ao buscar resumo XML:", err))
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


  async function handleAudit(e: React.FormEvent) {
    e.preventDefault()
    if (!auditPeriod) return
    
    setMessageType('info')
    setLogs([{ message: 'Gerando relatório de auditoria...', status: 'loading' }])
    setProcessingState('uploading_sped')
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/conciliacoes/${id}/auditoria/xml?mes=${auditPeriod}`)
      if (!res.ok) throw new Error('Erro ao gerar auditoria')
      const data = await res.json()
      setAuditReport(data)
      
      setLogs([{ message: 'Auditoria concluída com sucesso.', status: 'done' }])
      setTimeout(() => setProcessingState('idle'), 1000)
    } catch (err: any) {
      setLogs([{ message: err.message, status: 'error' }])
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

  const handleDeleteCompany = async () => {
    if (!confirm(`Tem certeza que deseja EXCLUIR a empresa ${company.razao_social} e TODOS os dados importados (XMLs, SPEDs e Históricos)? Esta ação não pode ser desfeita.`)) {
      return
    }
    
    setIsDeleting(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}`, {
        method: 'DELETE'
      })
      if (!res.ok) {
        throw new Error('Erro ao excluir empresa')
      }
      router.push('/companies')
    } catch (err: any) {
      alert(err.message)
      setIsDeleting(false)
    }
  }

  const isProcessing = processingState !== 'idle'

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
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
        <button
          onClick={handleDeleteCompany}
          disabled={isDeleting || isProcessing}
          className="bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20 px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-colors disabled:opacity-50"
        >
          {isDeleting ? 'Excluindo...' : (
             <>
               <AlertCircle size={16} /> Excluir Empresa
             </>
          )}
        </button>
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

      {/* Tabs */}
      <div className="flex gap-2 border-b border-white/10 pb-2">
        <button
          onClick={() => setActiveTab('conciliacao')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'conciliacao' ? 'bg-[var(--gold)] text-black' : 'text-[var(--foreground-muted)] hover:bg-white/5'}`}
        >
          Conciliação SPED
        </button>
        <button
          onClick={() => setActiveTab('base_dados')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'base_dados' ? 'bg-[var(--gold)] text-black' : 'text-[var(--foreground-muted)] hover:bg-white/5'}`}
        >
          Base de XMLs
        </button>
        <button
          onClick={() => setActiveTab('auditoria')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'auditoria' ? 'bg-[var(--gold)] text-black' : 'text-[var(--foreground-muted)] hover:bg-white/5'}`}
        >
          Auditoria (Relatório Reverso)
        </button>
      </div>

       {activeTab === 'conciliacao' && (
        <>
          <div className="glass-card rounded-2xl p-8 gold-accent relative z-20">
            {/* Loading overlay effect */}
            {isProcessing && (
              <div className="absolute inset-0 rounded-2xl bg-black/80 backdrop-blur-md z-30 flex flex-col items-center justify-center p-8">
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
                  <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">Período (YYYY-MM)</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={periodo}
                      onChange={e => setPeriodo(e.target.value)}
                      placeholder="Ex: 2026-05"
                      className="input-field w-full !pl-12 cursor-pointer"
                      required
                      disabled={isProcessing}
                      onClick={() => setIsCalendarOpen(!isCalendarOpen)}
                      readOnly
                    />
                    <Calendar size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--foreground-muted)]" />
                    
                    {isCalendarOpen && (
                      <div className="absolute z-50 mt-2 p-4 bg-[#111111] border border-white/10 rounded-xl shadow-2xl w-64" data-testid="calendar-popup">
                        <div className="flex justify-between items-center mb-4">
                          <button type="button" onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))} className="p-1 text-[var(--foreground-muted)] hover:text-white" data-testid="prev-month-btn"><ChevronLeft size={16} /></button>
                          <span className="font-bold text-sm">{currentMonth.toLocaleString('pt-BR', { month: 'long', year: 'numeric' }).toUpperCase()}</span>
                          <button type="button" onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))} className="p-1 text-[var(--foreground-muted)] hover:text-white" data-testid="next-month-btn"><ChevronRight size={16} /></button>
                        </div>
                        <div className="grid grid-cols-7 gap-1 mb-2 text-center text-xs font-medium text-[var(--foreground-muted)]">
                          <div>D</div><div>S</div><div>T</div><div>Q</div><div>Q</div><div>S</div><div>S</div>
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
              
              <div className="flex flex-col justify-center mb-6">
                <label className="flex items-center gap-3 cursor-pointer">
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
                  Desmarque se a API estiver fora do ar ou se você já importou os XMLs na aba "Base de XMLs".
                </p>
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

          {/* Histórico de Conciliações */}
          <div className="mt-12">
            <h2 className="text-xl font-bold text-[var(--foreground)] flex items-center gap-2 mb-6">
              <Calendar size={20} className="text-[var(--gold)]" /> Histórico de Conciliações
            </h2>
            {history.length === 0 ? (
              <div className="glass-card rounded-xl p-8 text-center text-[var(--foreground-muted)]">
                Nenhuma conciliação processada para esta empresa ainda.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {history.map((h, idx) => (
                  <div key={idx} className="glass-card rounded-xl p-6 relative group border border-white/5 hover:border-[var(--gold-border)] transition-all flex flex-col">
                    <div className="flex justify-between items-start mb-4">
                      <div className="text-2xl font-bold text-[var(--foreground)]">{h.periodo}</div>
                      <Link href={`/reconciliations/${id}/${h.periodo}`} className="text-xs font-bold text-[var(--gold)] bg-[var(--gold-glow)] px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                        Ver Relatório
                      </Link>
                    </div>
                    <div className="space-y-2 text-sm flex-grow">
                      <div className="flex justify-between">
                        <span className="text-[var(--foreground-muted)]">Total Registros</span>
                        <span className="text-[var(--foreground)] font-medium">{Number(h.total).toLocaleString('pt-BR')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--foreground-muted)]">Conciliados (OK)</span>
                        <span className="text-green-400 font-medium">{Number(h.ok).toLocaleString('pt-BR')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--foreground-muted)]">Faltantes no SPED</span>
                        <span className="text-red-400 font-medium">{Number(h.faltante || 0).toLocaleString('pt-BR')}</span>
                      </div>
                    </div>
                    {h.last_run && (
                      <div className="mt-4 pt-4 border-t border-white/10 text-xs text-[var(--foreground-muted)]">
                        Última execução: {new Date(h.last_run + (h.last_run.endsWith('Z') ? '' : 'Z')).toLocaleDateString('pt-BR')} às {new Date(h.last_run + (h.last_run.endsWith('Z') ? '' : 'Z')).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Tab: Base de Dados (XMLs) */}
      {activeTab === 'base_dados' && (
        <div className="space-y-6">
          <div className="glass-card rounded-2xl p-8 relative">
            {isProcessing && processingState === 'uploading_xml' && (
              <div className="absolute inset-0 rounded-2xl bg-black/80 backdrop-blur-md z-10 flex flex-col items-center justify-center p-8">
                 <div className="bg-[var(--background-card)] border border-[var(--gold-border)] rounded-2xl p-6 w-full max-w-md shadow-2xl">
                   <h3 className="text-xl font-bold text-[var(--gold)] mb-6 flex items-center gap-2">
                     <Code size={24} className="animate-pulse" /> Importando XMLs
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
            <h2 className="text-2xl font-bold text-[var(--foreground)] mb-6 flex items-center gap-2">
              <Code size={24} className="text-[var(--gold)]" /> Upload de XMLs (Lote)
            </h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">Arquivos XML ou ZIP</label>
                <div className="relative">
                  <input
                    type="file"
                    multiple
                    accept=".xml,.zip"
                    onChange={(e) => setXmlFilesMain(e.target.files)}
                    className="input-field w-full file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-[var(--gold)] file:text-black hover:file:bg-[var(--gold-glow)]"
                  />
                </div>
                <p className="text-xs text-[var(--foreground-muted)] mt-2">Você pode importar os XMLs separadamente aqui. Eles ficarão salvos na base global da empresa.</p>
              </div>
              <button 
                type="button"
                onClick={async () => {
                  if (!xmlFilesMain || xmlFilesMain.length === 0) return;
                  setMessageType('info');
                  setLogs([{ message: 'Enviando arquivos XML em lote...', status: 'loading' }]);
                  setProcessingState('uploading_xml');
                  const formDataXml = new FormData();
                  for (let i = 0; i < xmlFilesMain.length; i++) {
                    formDataXml.append('files', xmlFilesMain[i]);
                  }
                  try {
                    const xmlRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}/xml/upload`, {
                      method: 'POST',
                      body: formDataXml,
                    });
                    if (!xmlRes.ok) {
                      let errMsg = 'Erro ao fazer upload dos XMLs';
                      try {
                        const errData = await xmlRes.json();
                        if (errData && errData.detail) errMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
                      } catch (e) {}
                      throw new Error(errMsg);
                    }
                    const xmlResData = await xmlRes.json();
                    
                    if (xmlResData.results) {
                      const successCount = xmlResData.results.filter((r: any) => r.status === 'success').length;
                      const errorCount = xmlResData.results.filter((r: any) => r.status === 'error').length;
                      const errors = xmlResData.results.filter((r: any) => r.status === 'error');
                      
                      setLogs([{ 
                        message: `${successCount} XMLs importados. ${errorCount > 0 ? `${errorCount} falharam.` : ''}`, 
                        status: errorCount > 0 && successCount === 0 ? 'error' : 'done' 
                      }]);

                      if (errorCount > 0) {
                        console.error("Erros na importação:", errors);
                        setMessage(`${errorCount} arquivo(s) ignorado(s). Motivo comum: Não é uma NF-e modelo 55/65, é arquivo de cancelamento, ou está corrompido. Ex: ${errors[0].filename} - ${errors[0].message}`);
                        setMessageType('error');
                      } else {
                        setMessage('');
                      }
                    } else {
                      setLogs([{ message: 'Upload concluído, mas formato de resposta inesperado.', status: 'done' }]);
                    }
                    
                    // Refresh summary
                    fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}/xml/summary`)
                      .then(res => {
                        if (!res.ok) throw new Error(`Erro ${res.status}`);
                        return res.json();
                      })
                      .then(data => {
                        setXmlSummary(data);
                        fetchXmlsForMonth(null);
                      })
                      .catch(err => console.error("Erro ao atualizar resumo XML:", err));
                      
                    setTimeout(() => setProcessingState('idle'), 4000);
                  } catch(e: any) {
                    setLogs([{ message: e.message, status: 'error' }]);
                    setMessageType('error');
                    setMessage(e.message);
                    setProcessingState('idle');
                  }
                }}
                disabled={!xmlFilesMain || isProcessing}
                className="btn-gold w-full py-3 rounded-xl font-bold text-black"
              >
                Importar XMLs para a Base
              </button>
            </div>
          </div>

          <div className="glass-card rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-[var(--foreground)] mb-6">Volume de XMLs na Base</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
              {xmlSummary.map((sum, i) => (
                <div 
                  key={i} 
                  onClick={() => fetchXmlsForMonth(selectedXmlMonth === sum.mes ? null : sum.mes)}
                  className={`bg-white/5 rounded-xl p-5 border cursor-pointer transition-all ${selectedXmlMonth === sum.mes ? 'border-[var(--gold)] bg-[var(--gold-glow)] shadow-[0_0_15px_rgba(201,168,76,0.2)]' : 'border-white/10 hover:border-[var(--gold-border)] hover:bg-[var(--card-bg)]'}`}
                >
                  <div className="text-[var(--gold)] font-bold text-lg mb-2">{sum.mes}</div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-[var(--foreground-muted)]">Quantidade:</span>
                    <span className="font-semibold text-white">{sum.quantidade} XMLs</span>
                  </div>
                  <div className="flex justify-between items-center text-sm mt-1">
                    <span className="text-[var(--foreground-muted)]">Total:</span>
                    <span className="font-semibold text-white">
                      {sum.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </span>
                  </div>
                </div>
              ))}
              {xmlSummary.length === 0 && (
                <div className="col-span-full text-center py-8 text-[var(--foreground-muted)]">Nenhum XML na base de dados.</div>
              )}
            </div>

            {/* XML List Grid */}
            <div className="mt-8 border-t border-white/10 pt-8">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-[var(--foreground)]">
                  {selectedXmlMonth ? `Registros de ${selectedXmlMonth}` : 'Todos os Registros (Últimos 1000)'}
                </h3>
                {selectedXmlMonth && (
                  <button onClick={() => fetchXmlsForMonth(null)} className="text-sm text-[var(--gold)] hover:underline">
                    Ver Todos
                  </button>
                )}
              </div>
              
              <div className="overflow-x-auto rounded-xl border border-[var(--card-border)] bg-black/40">
                <table className="min-w-full text-left whitespace-nowrap">
                  <thead className="table-header bg-[var(--sidebar-bg)] border-b border-[var(--card-border)]">
                    <tr>
                      <th className="px-6 py-4 text-xs font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">Status</th>
                      <th className="px-6 py-4 text-xs font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">Chave NF-e</th>
                      <th className="px-6 py-4 text-xs font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">Série/Num</th>
                      <th className="px-6 py-4 text-xs font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">Emissão</th>
                      <th className="px-6 py-4 text-xs font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">Valor</th>
                      <th className="px-6 py-4 text-xs font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">Origem</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {loadingXmls ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-[var(--foreground-muted)]">
                          Carregando registros...
                        </td>
                      </tr>
                    ) : xmlList.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-[var(--foreground-muted)]">
                          Nenhum registro encontrado.
                        </td>
                      </tr>
                    ) : (
                      xmlList.map((xml, idx) => (
                        <tr key={idx} className="hover:bg-white/5 transition-colors">
                          <td className="px-6 py-4">
                            {xml.situacao === 'CANCELADA' ? (
                              <span className="badge badge-missing">{xml.situacao}</span>
                            ) : (
                              <span className="badge badge-ok">{xml.situacao || 'AUTORIZADA'}</span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-sm font-mono text-[var(--foreground)]">{xml.chave_nfe}</td>
                          <td className="px-6 py-4 text-sm text-[var(--foreground)]">{xml.serie} / {xml.numero}</td>
                          <td className="px-6 py-4 text-sm text-[var(--foreground)]">{xml.data_emissao}</td>
                          <td className="px-6 py-4 text-sm font-semibold text-[var(--foreground)]">
                            {xml.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                          </td>
                          <td className="px-6 py-4 text-sm text-[var(--foreground-muted)]">{xml.origem || 'Upload'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* End of Base de Dados Tab */}

      {/* Tab: Auditoria */}
      {activeTab === 'auditoria' && (
        <div className="space-y-6">
          <div className="glass-card rounded-2xl p-8 relative">
            {isProcessing && processingState === 'uploading_sped' && (
              <div className="absolute inset-0 rounded-2xl bg-black/80 backdrop-blur-md z-10 flex flex-col items-center justify-center p-8">
                 <div className="bg-[var(--background-card)] border border-[var(--gold-border)] rounded-2xl p-6 w-full max-w-md shadow-2xl">
                   <h3 className="text-xl font-bold text-[var(--gold)] mb-6 flex items-center gap-2">
                     <AlertCircle size={24} className="animate-pulse" /> Gerando Relatório
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
            <h2 className="text-2xl font-bold text-[var(--foreground)] mb-2 flex items-center gap-2">
              <AlertCircle size={24} className="text-[var(--gold)]" /> Relatório Reverso de Auditoria
            </h2>
            <p className="text-sm text-[var(--foreground-muted)] mb-6">
              Descubra em quais meses os XMLs emitidos em um determinado período foram escriturados no SPED.
            </p>
            <form onSubmit={handleAudit} className="flex items-end gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">Mês de Emissão (YYYY-MM)</label>
                <input
                  type="text"
                  placeholder="Ex: 2026-01"
                  value={auditPeriod}
                  onChange={(e) => setAuditPeriod(e.target.value)}
                  className="input-field w-full"
                />
              </div>
              <button type="submit" disabled={isProcessing || !auditPeriod} className="btn-gold px-8 py-3 rounded-xl font-bold text-black">
                Gerar Relatório
              </button>
            </form>
          </div>

          {auditReport && (
            <div className="glass-card rounded-2xl p-8">
              <div className="flex flex-col sm:flex-row gap-4 justify-between mb-8">
                <div className="bg-white/5 p-4 rounded-xl text-center flex-1 border border-white/10">
                  <div className="text-[var(--foreground-muted)] text-sm mb-1">Total Emitidas</div>
                  <div className="text-2xl font-bold text-white">{auditReport.total_xmls}</div>
                </div>
                <div className="bg-green-500/10 p-4 rounded-xl text-center flex-1 border border-green-500/20">
                  <div className="text-green-400 text-sm mb-1">Foram Escrituradas</div>
                  <div className="text-2xl font-bold text-green-400">{auditReport.total_escriturados}</div>
                </div>
                <div className="bg-red-500/10 p-4 rounded-xl text-center flex-1 border border-red-500/20">
                  <div className="text-red-400 text-sm mb-1">Não Escrituradas</div>
                  <div className="text-2xl font-bold text-red-400">{auditReport.total_nao_escriturados}</div>
                </div>
              </div>

              <div className="overflow-x-auto rounded-xl border border-white/10">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-white/5 border-b border-white/10">
                      <th className="p-4 text-xs font-semibold text-[var(--foreground-muted)] tracking-wider">CHAVE NF-E</th>
                      <th className="p-4 text-xs font-semibold text-[var(--foreground-muted)] tracking-wider">DATA EMISSÃO</th>
                      <th className="p-4 text-xs font-semibold text-[var(--foreground-muted)] tracking-wider text-right">VALOR</th>
                      <th className="p-4 text-xs font-semibold text-[var(--foreground-muted)] tracking-wider">STATUS SEFAZ</th>
                      <th className="p-4 text-xs font-semibold text-[var(--foreground-muted)] tracking-wider">SPED</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {auditReport.detalhes.map((item: any) => (
                      <tr key={item.id} className="hover:bg-white/5 transition-colors">
                        <td className="p-4 text-sm font-medium">{item.chave_nfe}</td>
                        <td className="p-4 text-sm text-[var(--foreground-muted)]">{item.data_emissao}</td>
                        <td className="p-4 text-sm text-right">{item.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td>
                        <td className="p-4 text-sm">
                          <span className={`px-2 py-1 rounded text-xs ${item.situacao_sefaz === 'CANCELADA' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'}`}>
                            {item.situacao_sefaz}
                          </span>
                        </td>
                        <td className="p-4 text-sm">
                          {item.escriturado ? (
                            <div className="flex gap-1 flex-wrap">
                              {item.speds_encontrados.map((s: any, idx: number) => (
                                <span key={idx} className="bg-green-500/20 text-green-400 px-2 py-1 rounded text-xs">
                                  {s.periodo} ({s.status})
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="bg-red-500/20 text-red-400 px-2 py-1 rounded text-xs">Não encontrada</span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {auditReport.detalhes.length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-[var(--foreground-muted)]">Nenhum XML encontrado para este mês.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
      {/* End of Auditoria Tab */}
    </div>
  )
}
