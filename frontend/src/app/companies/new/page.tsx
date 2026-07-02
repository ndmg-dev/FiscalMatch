"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Upload } from 'react-feather'

export default function NewCompanyPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError('')

    const formData = new FormData(e.currentTarget)
    const payload = {
      cnpj: formData.get('cnpj'),
      razao_social: formData.get('razao_social'),
      uf: formData.get('uf') || null,
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/empresas/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Erro ao criar empresa')
      }

      router.push('/companies')
    } catch (err: any) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto space-y-6 mt-8">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/companies" className="text-[var(--foreground-muted)] hover:text-[var(--gold)] transition-colors">
          <ArrowLeft size={22} />
        </Link>
        <h1 className="page-title">
          <Upload />
          Nova Empresa
        </h1>
      </div>

      <div className="glass-card rounded-2xl p-8">
        {error && (
          <div className="alert-error mb-6">{error}</div>
        )}

        <form onSubmit={onSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">
              CNPJ (Apenas números)
            </label>
            <input
              name="cnpj"
              required
              maxLength={14}
              pattern="\d{14}"
              className="input-field"
              placeholder="00000000000000"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">
              Razão Social
            </label>
            <input
              name="razao_social"
              required
              className="input-field"
              placeholder="Minha Empresa LTDA"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">
              UF (Opcional)
            </label>
            <input
              name="uf"
              maxLength={2}
              className="input-field uppercase"
              placeholder="SP"
            />
          </div>

          <div className="pt-4">
            <button
              type="submit"
              disabled={loading}
              className="w-full btn-gold px-4 py-3 rounded-lg text-center"
            >
              {loading ? 'Salvando...' : 'Salvar Empresa'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
