from sqlalchemy import Column, String, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cnpj = Column(String(14), unique=True, index=True, nullable=False)
    razao_social = Column(String(255), nullable=False)
    uf = Column(String(2), nullable=True)
    certificado_configurado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("now()"))
