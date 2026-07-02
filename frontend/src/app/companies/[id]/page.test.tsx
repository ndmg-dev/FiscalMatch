import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import CompanyDetailsPage from './page'
import '@testing-library/jest-dom'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useParams: () => ({ id: '123' }),
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

describe('CompanyDetailsPage - Calendar Modal', () => {
  beforeEach(() => {
    // Mock the fetch call for the company data
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ id: '123', razao_social: 'Teste LTDA' }),
      })
    ) as jest.Mock
  })

  afterEach(() => {
    jest.resetAllMocks()
  })

  it('deve abrir e fechar o modal de calendário', async () => {
    render(<CompanyDetailsPage />)
    
    // O botão deve aparecer após o fetch
    const openBtn = await screen.findByTestId('open-calendar-btn')
    
    // O modal não deve estar visível inicialmente
    expect(screen.queryByTestId('calendar-modal')).not.toBeInTheDocument()

    // Clica no botão para abrir o calendário
    fireEvent.click(openBtn)

    // O modal deve aparecer
    expect(await screen.findByTestId('calendar-modal')).toBeInTheDocument()

    // Clica no botão de cancelar
    const closeBtn = screen.getByTestId('close-calendar-btn')
    fireEvent.click(closeBtn)

    // O modal deve desaparecer
    expect(screen.queryByTestId('calendar-modal')).not.toBeInTheDocument()
  })

  it('deve selecionar um dia e atualizar o campo de período', async () => {
    render(<CompanyDetailsPage />)
    
    // O botão deve aparecer após o fetch
    const openBtn = await screen.findByTestId('open-calendar-btn')
    
    // Abre o calendário
    fireEvent.click(openBtn)

    // O modal deve aparecer
    expect(await screen.findByTestId('calendar-modal')).toBeInTheDocument()

    // Clica no dia 15
    const dayBtn = screen.getByTestId('day-15')
    fireEvent.click(dayBtn)

    // O modal deve fechar automaticamente após a seleção
    expect(screen.queryByTestId('calendar-modal')).not.toBeInTheDocument()

    // O botão deve mostrar a data no formato YYYY-MM
    // Para simplificar o teste, vamos verificar se o ano e mês atuais estão presentes
    const currentDate = new Date()
    const yyyy = currentDate.getFullYear()
    const mm = String(currentDate.getMonth() + 1).padStart(2, '0')
    const expectedPeriodo = `${yyyy}-${mm}`
    
    expect(openBtn).toHaveTextContent(expectedPeriodo)
  })
})
