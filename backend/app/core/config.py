from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FiscalMatch Pre-MVP"
    
    # DB
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "fiscalmatch"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[str] = None
    
    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "admin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET: str = "fiscalmatch"
    MINIO_SECURE: bool = False

    # SIEG Integration
    SIEG_API_KEY: str | None = None
    SIEG_EMAIL: str | None = None
    SIEG_API_URL: str = "https://api.sieg.com/"

    # Autenticação — mesmo segredo do JWT_SECRET do CRM (backend-fastapi). O
    # frontend nativo embutido no CRM (src/systems/conciliacao-fiscal) envia
    # o token de sessão do próprio CRM; esta API só valida a assinatura e a
    # expiração, sem depender da tabela de usuários do CRM (que fica em outro
    # banco). Sem isso, dado fiscal real de cliente (NF-e/SPED) ficava
    # acessível pra qualquer um com a URL — não havia nenhuma auth antes.
    JWT_SECRET: str = ""
    # String separada por vírgula (não list[str]): pydantic-settings exigiria
    # JSON pra um campo de lista, e o resto do .env deste projeto usa valores
    # simples — mais fácil manter consistente.
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
