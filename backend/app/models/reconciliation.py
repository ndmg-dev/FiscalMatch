from sqlalchemy import Column, String, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from app.core.database import Base

class Conciliacao(Base):
    __tablename__ = "conciliacoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    periodo = Column(String(7), nullable=False, index=True)
    documento_fiscal_id = Column(UUID(as_uuid=True), ForeignKey("documentos_xml.id", ondelete="SET NULL"), nullable=True)
    documento_sped_id = Column(UUID(as_uuid=True), ForeignKey("documentos_sped.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=False, index=True) # OK, NAO_ATRIBUIDA, FALTANTE, DIVERGENTE, IGNORADA_POR_REGRA
    diferencas_json = Column(JSONB, nullable=True)
    observacao = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("now()"))
