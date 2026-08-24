from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.core.security import get_current_crm_user
import app.models  # to ensure models are loaded
from app.api.endpoints import companies, sped, xml, reconciliations, sieg, dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    # Criar índices faltantes para evitar scans completos da tabela (Table Scans O(N))
    # nas validações de integridade referencial do Postgres (causadoras dos travamentos)
    with engine.begin() as conn:
        from sqlalchemy import text
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_conciliacoes_doc_fiscal ON conciliacoes(documento_fiscal_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_conciliacoes_doc_sped ON conciliacoes(documento_sped_id);"))
        
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS: lista explícita (não mais "*") — a API carrega documento fiscal real
# de cliente, então precisa saber exatamente quem pode chamar. O CRM embute
# o frontend nativamente e é a única origem legítima hoje.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Toda rota de negócio exige o token de sessão do CRM (ver app/core/security.py)
# — antes disso a API não tinha autenticação nenhuma.
_auth = [Depends(get_current_crm_user)]

app.include_router(companies.router, prefix=f"{settings.API_V1_STR}/empresas", tags=["Empresas"], dependencies=_auth)
app.include_router(sped.router, prefix=f"{settings.API_V1_STR}/empresas/{{empresa_id}}/sped", tags=["SPED"], dependencies=_auth)
app.include_router(xml.router, prefix=f"{settings.API_V1_STR}/empresas/{{empresa_id}}/xml", tags=["XML"], dependencies=_auth)
app.include_router(sieg.router, prefix=f"{settings.API_V1_STR}/empresas/{{empresa_id}}/integracoes/sieg", tags=["SIEG"], dependencies=_auth)
app.include_router(reconciliations.router, prefix=f"{settings.API_V1_STR}/conciliacoes", tags=["Conciliações"], dependencies=_auth)
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard"], dependencies=_auth)

@app.get("/")
def root():
    return {"message": "Welcome to FiscalMatch API"}
