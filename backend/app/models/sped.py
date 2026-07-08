from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric, text, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class ArquivoSped(Base):
    __tablename__ = "arquivos_sped"
    __table_args__ = (
        Index('ix_arquivos_sped_empresa_periodo', 'empresa_id', 'periodo'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    periodo = Column(String(7), nullable=False, index=True) # YYYY-MM
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    status = Column(String(50), default="PENDING") # PENDING, PARSING, COMPLETED, ERROR
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("now()"))

class DocumentoSped(Base):
    __tablename__ = "documentos_sped"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    arquivo_sped_id = Column(UUID(as_uuid=True), ForeignKey("arquivos_sped.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    chave_nfe = Column(String(44), nullable=True, index=True)
    ind_oper = Column(String(1), nullable=False) # 0-Entrada, 1-Saída
    ind_emit = Column(String(1), nullable=False) # 0-Emissão Própria, 1-Terceiros
    cod_part = Column(String(60), nullable=True)
    nome_part = Column(String(255), nullable=True)
    cnpj_part = Column(String(14), nullable=True, index=True)
    modelo = Column(String(2), nullable=False, index=True)
    cod_sit = Column(String(2), nullable=False)
    serie = Column(String(3), nullable=True, index=True)
    numero = Column(Integer, nullable=False, index=True)
    data_doc = Column(DateTime, nullable=True)
    data_entrada_saida = Column(DateTime, nullable=True)
    valor_doc = Column(Numeric(15, 2), nullable=True)
    linha_original = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("now()"))
