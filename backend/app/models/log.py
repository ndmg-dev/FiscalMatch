from sqlalchemy import Column, String, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class LogProcessamento(Base):
    __tablename__ = "logs_processamento"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(255), nullable=True)
    tipo = Column(String(50), nullable=False) # PARSE_SPED, PARSE_XML, RECONCILIACAO, SIEG_SYNC
    status = Column(String(50), nullable=False) # SUCCESS, ERROR, WARNING
    mensagem = Column(String, nullable=False)
    detalhes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("now()"))
