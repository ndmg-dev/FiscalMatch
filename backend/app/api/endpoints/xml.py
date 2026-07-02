from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.storage import storage
from app.models.company import Empresa
from redis import Redis
from rq import Queue
from app.core.config import settings
import uuid
from typing import List

router = APIRouter()
redis_conn = Redis.from_url(settings.REDIS_URL)
q = Queue(connection=redis_conn)

@router.post("/upload")
def upload_xml(
    empresa_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    from app.services.xml_parser import XMLParser
    from app.models.xml import DocumentoXML
    import traceback

    results = []
    
    for file in files:
        try:
            file_bytes = file.file.read()
            storage_path = f"xml/{empresa_id}/{uuid.uuid4()}_{file.filename}"
            storage.upload_file(storage_path, file_bytes)
            
            parsed = XMLParser.parse(file_bytes)
            
            existing = db.query(DocumentoXML).filter(DocumentoXML.chave_nfe == parsed["chave_nfe"]).first()
            if existing:
                for k, v in parsed.items():
                    setattr(existing, k, v)
                existing.origem = "UPLOAD"
                existing.storage_path = storage_path
            else:
                new_xml = DocumentoXML(
                    empresa_id=empresa_id,
                    origem="UPLOAD",
                    storage_path=storage_path,
                    **parsed
                )
                db.add(new_xml)
                
            db.commit()
            
            results.append({
                "filename": file.filename,
                "status": "success",
                "chave_nfe": parsed.get("chave_nfe"),
                "cnpj_emitente": parsed.get("cnpj_emitente"),
                "data_emissao": parsed.get("data_emissao").isoformat() if parsed.get("data_emissao") else None,
                "valor_total": parsed.get("valor_total"),
                "message": "XML processado com sucesso"
            })
            
        except Exception as e:
            db.rollback()
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e)
            })

    return {
        "message": f"{len(files)} arquivos processados.",
        "results": results
    }
