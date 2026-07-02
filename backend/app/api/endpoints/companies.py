from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.company import Empresa
from app.schemas.company import EmpresaCreate, EmpresaResponse

router = APIRouter()

@router.post("/", response_model=EmpresaResponse)
def create_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    db_empresa = db.query(Empresa).filter(Empresa.cnpj == empresa.cnpj).first()
    if db_empresa:
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    
    new_empresa = Empresa(**empresa.model_dump())
    db.add(new_empresa)
    db.commit()
    db.refresh(new_empresa)
    return new_empresa

@router.get("/", response_model=List[EmpresaResponse])
def list_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).all()

@router.get("/{empresa_id}", response_model=EmpresaResponse)
def get_empresa(empresa_id: str, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa
