from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric, text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class DocumentoXML(Base):
    __tablename__ = "documentos_xml"
    __table_args__ = (
        UniqueConstraint('empresa_id', 'chave_nfe', name='uq_xml_empresa_chave'),
        Index('ix_xml_data_emissao', 'data_emissao'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    origem = Column(String(50), nullable=False) # UPLOAD, SIEG
    chave_nfe = Column(String(44), nullable=False, index=True)
    modelo = Column(String(2), nullable=False, index=True)
    serie = Column(String(3), nullable=True, index=True)
    numero = Column(Integer, nullable=False, index=True)
    cnpj_emitente = Column(String(14), nullable=False, index=True)
    cnpj_destinatario = Column(String(14), nullable=True, index=True)
    data_emissao = Column(DateTime, nullable=True)
    valor_total = Column(Numeric(15, 2), nullable=True)
    situacao = Column(String(50), nullable=True)
    storage_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("now()"))
