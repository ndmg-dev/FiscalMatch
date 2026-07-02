# FiscalMatch Pre-MVP

Uma aplicação web para reconciliar documentos fiscais XML (NF-e modelo 55) contra registros do SPED Fiscal.

## Tecnologias Utilizadas

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Redis, RQ
- **Frontend**: Next.js 14+, React, Tailwind CSS
- **Banco de Dados**: PostgreSQL
- **Armazenamento**: MinIO (S3 compatible)
- **Infraestrutura**: Docker e Docker Compose

## Pré-requisitos

- Docker e Docker Compose instalados
- Node.js 20+ (apenas se for rodar o frontend localmente fora do container)

## Como Executar Localmente

1. Clone o repositório.
2. Copie o arquivo `.env.example` para `.env` na raiz do projeto:
   ```bash
   cp .env.example .env
   ```
3. Suba a infraestrutura usando o Docker Compose:
   ```bash
   docker compose up -d
   ```
4. A aplicação estará disponível em:
   - **Frontend**: [http://localhost:3000](http://localhost:3000)
   - **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **MinIO Console**: [http://localhost:9001](http://localhost:9001) (Usuário: `admin`, Senha: `minioadmin`)

## Limitações Conhecidas do MVP

- Foco exclusivo em NF-e modelo 55 (e 65 fallback).
- A integração com SIEG é atualmente um "stub" (placeholder arquitetural). Para ativar na Fase 2, preencha as variáveis de ambiente `SIEG_API_KEY` e implemente a chamada HTTP no serviço em `backend/app/services/sieg_connector.py`.
- Autenticação e Multi-Tenancy avançado não foram incluídos. O sistema funciona baseado na identificação das empresas por ID.

## Executando os Testes

Os testes do backend focam na camada crítica de "parsers":
```bash
# Na pasta backend, crie um venv com python 3.11+ e ative-o
pip install -r requirements.txt
pytest tests/
```
