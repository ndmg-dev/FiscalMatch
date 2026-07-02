from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.sieg_connector import SiegConnector

router = APIRouter()

@router.post("/sincronizar")
def sync_sieg(empresa_id: str, periodo: str, db: Session = Depends(get_db)):
    """
    Endpoint para acionar a sincronização com o SIEG.
    MVP: Stub apenas.
    """
    # Fetch empresa to get CNPJ
    from app.models.company import Empresa
    from fastapi import HTTPException
    
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
    sieg = SiegConnector()
    result = sieg.sync_documents(empresa.cnpj, periodo)
    
    # In a real integration, we would save downloaded XMLs and enqueue processing here
    
    return result
