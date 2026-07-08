from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
import app.models  # to ensure models are loaded
from app.api.endpoints import companies, sped, xml, reconciliations, sieg, dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In MVP allow all, in prod define explicit origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(companies.router, prefix=f"{settings.API_V1_STR}/empresas", tags=["Empresas"])
app.include_router(sped.router, prefix=f"{settings.API_V1_STR}/empresas/{{empresa_id}}/sped", tags=["SPED"])
app.include_router(xml.router, prefix=f"{settings.API_V1_STR}/empresas/{{empresa_id}}/xml", tags=["XML"])
app.include_router(sieg.router, prefix=f"{settings.API_V1_STR}/empresas/{{empresa_id}}/integracoes/sieg", tags=["SIEG"])
app.include_router(reconciliations.router, prefix=f"{settings.API_V1_STR}/conciliacoes", tags=["Conciliações"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard"])

@app.get("/")
def root():
    return {"message": "Welcome to FiscalMatch API"}
