from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.storage import storage
from app.models.sped import ArquivoSped, DocumentoSped
from app.models.company import Empresa
from app.services.sped_parser import SpedParser
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload")
def upload_sped(
    empresa_id: str,
    periodo: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    file_bytes = file.file.read()
    
    # Upload to storage for archival
    storage_path = f"sped/{empresa_id}/{periodo}/{uuid.uuid4()}_{file.filename}"
    try:
        storage.upload_file(storage_path, file_bytes)
    except Exception as e:
        logger.warning(f"MinIO upload failed (non-critical): {e}")

    # Remove old SPED files and their parsed documents for the same empresa+periodo
    old_arquivos = db.query(ArquivoSped).filter(
        ArquivoSped.empresa_id == empresa.id,
        ArquivoSped.periodo == periodo
    ).all()
    for old in old_arquivos:
        db.query(DocumentoSped).filter(DocumentoSped.arquivo_sped_id == old.id).delete(synchronize_session=False)
        db.delete(old)
    if old_arquivos:
        db.commit()

    arquivo_sped = ArquivoSped(
        empresa_id=empresa.id,
        periodo=periodo,
        original_filename=file.filename,
        storage_path=storage_path,
        status="PARSING"
    )
    db.add(arquivo_sped)
    db.commit()
    db.refresh(arquivo_sped)

    # Parse SPED directly from memory (no MinIO round-trip)
    try:
        content = file_bytes.decode('windows-1252', errors='replace')
        parser = SpedParser()
        result = parser.parse(content)

        docs_to_insert = []
        for doc in result["documents"]:
            doc_data = {
                "id": uuid.uuid4(),
                "arquivo_sped_id": arquivo_sped.id,
                "empresa_id": empresa.id,
            }
            doc_data.update(doc)
            docs_to_insert.append(doc_data)
        
        if docs_to_insert:
            # chunking insertions to avoid memory spikes and DB locks
            chunk_size = 5000
            for i in range(0, len(docs_to_insert), chunk_size):
                db.bulk_insert_mappings(DocumentoSped, docs_to_insert[i:i + chunk_size])

        arquivo_sped.status = "COMPLETED"
        db.commit()
        
        logger.info(f"SPED processado: {len(docs_to_insert)} registros C100")
        return {
            "message": "Arquivo recebido e processado com sucesso",
            "arquivo_sped_id": str(arquivo_sped.id),
            "registros_c100": len(docs_to_insert)
        }

    except Exception as e:
        arquivo_sped.status = "ERROR"
        db.commit()
        logger.error(f"Erro ao processar SPED: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo SPED: {str(e)}")

