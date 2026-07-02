from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional
from datetime import datetime

class EmpresaBase(BaseModel):
    cnpj: str
    razao_social: str
    uf: Optional[str] = None

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: UUID
    certificado_configurado: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
