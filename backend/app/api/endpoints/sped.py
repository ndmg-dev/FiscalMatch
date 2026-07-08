from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.storage import storage
from app.models.sped import ArquivoSped, DocumentoSped
from app.models.company import Empresa
from app.services.sped_parser import SpedParser
import uuid
import logging
import io

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

    # Read file into memory for size calculation and dual-use (storage + parsing)
    file_bytes = file.file.read()
    file_size = len(file_bytes)
    
    # Upload to storage for archival using stream in a background daemon thread
    storage_path = f"sped/{empresa_id}/{periodo}/{uuid.uuid4()}_{file.filename}"
    
    def upload_bg():
        try:
            storage.upload_stream(storage_path, io.BytesIO(file_bytes), length=file_size)
        except Exception as e:
            logger.warning(f"MinIO upload failed (non-critical): {e}")
            
    import threading
    threading.Thread(target=upload_bg, daemon=True).start()

    try:
        from app.models.reconciliation import Conciliacao
        
        # Remove old SPED files and their parsed documents for the same empresa+periodo
        old_arquivos = db.query(ArquivoSped).filter(
            ArquivoSped.empresa_id == empresa.id,
            ArquivoSped.periodo == periodo
        ).all()
        
        # Prevent Postgres slow O(N) cascade SET NULL on conciliacoes
        db.query(Conciliacao).filter(
            Conciliacao.empresa_id == empresa.id,
            Conciliacao.periodo == periodo
        ).delete(synchronize_session=False)
        
        for old in old_arquivos:
            db.query(DocumentoSped).filter(DocumentoSped.arquivo_sped_id == old.id).delete(synchronize_session=False)
            db.delete(old)

        arquivo_sped = ArquivoSped(
            empresa_id=empresa.id,
            periodo=periodo,
            original_filename=file.filename,
            storage_path=storage_path,
            status="PARSING"
        )
        db.add(arquivo_sped)
        db.flush()

        # Parse SPED from in-memory bytes
        content_lines = file_bytes.decode('windows-1252', errors='replace').splitlines()
        parser = SpedParser()
        docs_generator = parser.parse_stream(content_lines)

        docs_chunk = []
        docs_inserted = 0
        chunk_size = 5000

        for doc in docs_generator:
            doc_data = {
                "id": uuid.uuid4(),
                "arquivo_sped_id": arquivo_sped.id,
                "empresa_id": empresa.id,
            }
            doc_data.update(doc)
            docs_chunk.append(doc_data)
            
            if len(docs_chunk) >= chunk_size:
                db.bulk_insert_mappings(DocumentoSped, docs_chunk)
                docs_inserted += len(docs_chunk)
                docs_chunk = []
                
        if docs_chunk:
            db.bulk_insert_mappings(DocumentoSped, docs_chunk)
            docs_inserted += len(docs_chunk)

        arquivo_sped.status = "COMPLETED"
        db.commit()
        
        logger.info(f"SPED processado: {docs_inserted} registros C100")
        return {
            "message": "Arquivo recebido e processado com sucesso",
            "arquivo_sped_id": str(arquivo_sped.id),
            "registros_c100": docs_inserted
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao processar SPED: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo SPED: {str(e)}")
