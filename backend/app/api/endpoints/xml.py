from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.storage import storage
from app.models.company import Empresa
from redis import Redis
from rq import Queue
from app.core.config import settings
import uuid
from typing import List
import traceback

router = APIRouter()
redis_conn = Redis.from_url(settings.REDIS_URL)
q = Queue(connection=redis_conn)

def upload_files_to_storage_bg(files_to_upload: list):
    """Background task to upload files to storage"""
    for storage_path, content in files_to_upload:
        try:
            storage.upload_file(storage_path, content)
        except Exception as e:
            print(f"Erro no upload em background do arquivo {storage_path}: {e}")

@router.post("/upload")
def upload_xml(
    empresa_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    from app.services.xml_parser import XMLParser
    from app.models.xml import DocumentoXML
    import zipfile
    import io

    results = []
    files_to_upload_bg = []
    
    # 1. Extrair e fazer o parser de todos os XMLs em memória
    parsed_xmls = []
    
    for file in files:
        file_bytes = file.file.read()

        if file.filename.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    for zip_info in z.infolist():
                        if zip_info.filename.lower().endswith('.xml'):
                            xml_bytes = z.read(zip_info.filename)
                            try:
                                parsed = XMLParser.parse(xml_bytes)
                                storage_path = f"xml/{empresa_id}/{uuid.uuid4()}_{zip_info.filename}"
                                parsed_xmls.append({
                                    "parsed": parsed,
                                    "filename": zip_info.filename,
                                    "storage_path": storage_path,
                                    "content": xml_bytes
                                })
                            except Exception as e:
                                results.append({
                                    "filename": zip_info.filename,
                                    "status": "error",
                                    "message": f"Erro no parse: {str(e)}"
                                })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": f"Erro ao ler arquivo ZIP: {str(e)}"
                })
        else:
            try:
                parsed = XMLParser.parse(file_bytes)
                storage_path = f"xml/{empresa_id}/{uuid.uuid4()}_{file.filename}"
                parsed_xmls.append({
                    "parsed": parsed,
                    "filename": file.filename,
                    "storage_path": storage_path,
                    "content": file_bytes
                })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": str(e)
                })

    if not parsed_xmls:
        return {
            "message": "Nenhum XML válido encontrado.",
            "results": results
        }

    # 2. Buscar no banco de dados quais chaves já existem (Batch Query)
    chaves = [item["parsed"]["chave_nfe"] for item in parsed_xmls if "chave_nfe" in item["parsed"]]
    existing_docs = db.query(DocumentoXML).filter(DocumentoXML.chave_nfe.in_(chaves)).all()
    existing_map = {doc.chave_nfe: doc for doc in existing_docs}

    # 3. Processar inserções e atualizações em memória
    new_docs = []
    
    for item in parsed_xmls:
        parsed = item["parsed"]
        chave = parsed.get("chave_nfe")
        filename = item["filename"]
        storage_path = item["storage_path"]
        
        if chave in existing_map:
            doc = existing_map[chave]
            for k, v in parsed.items():
                setattr(doc, k, v)
            doc.origem = "UPLOAD"
            doc.storage_path = storage_path
        else:
            new_doc = DocumentoXML(
                empresa_id=empresa_id,
                origem="UPLOAD",
                storage_path=storage_path,
                **parsed
            )
            new_docs.append(new_doc)
            # Add to map to prevent duplicates in the same batch
            existing_map[chave] = new_doc
            
        # Schedule physical upload
        files_to_upload_bg.append((storage_path, item["content"]))
        
        results.append({
            "filename": filename,
            "status": "success",
            "chave_nfe": chave,
            "cnpj_emitente": parsed.get("cnpj_emitente"),
            "message": "Processado com sucesso"
        })

    # 4. Salvar no banco em lote
    if new_docs:
        db.bulk_save_objects(new_docs)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar no banco de dados: {str(e)}")

    # 5. Agendar o upload para o MinIO em background
    if files_to_upload_bg:
        background_tasks.add_task(upload_files_to_storage_bg, files_to_upload_bg)

    return {
        "message": f"{len(results)} XMLs processados com sucesso.",
        "results": results
    }
