from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.storage import storage
from app.models.company import Empresa
import uuid
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB

def upload_files_to_storage_bg(files_to_upload: list):
    """Background task to upload files to storage"""
    for storage_path, content in files_to_upload:
        try:
            storage.upload_file(storage_path, content)
        except Exception as e:
            logger.error(f"Erro no upload em background do arquivo {storage_path}: {e}")

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

        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Arquivo excede o tamanho máximo de 500MB")

        if file.filename.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    for zip_info in z.infolist():
                        if '__MACOSX' in zip_info.filename or zip_info.filename.split('/')[-1].startswith('.'):
                            continue
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

    # 2. Buscar no banco de dados quais chaves já existem (Batch Query - em chunks)
    chaves = [item["parsed"]["chave_nfe"] for item in parsed_xmls if "chave_nfe" in item["parsed"]]
    existing_docs = []
    chunk_size = 1000
    for i in range(0, len(chaves), chunk_size):
        chunk = chaves[i:i + chunk_size]
        docs_chunk = db.query(DocumentoXML).filter(DocumentoXML.empresa_id == empresa_id, DocumentoXML.chave_nfe.in_(chunk)).all()
        existing_docs.extend(docs_chunk)
        
    existing_map = {doc.chave_nfe: doc for doc in existing_docs}

    # 3. Processar inserções e atualizações em memória
    new_docs = []
    docs_to_update = []
    
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
            docs_to_update.append(doc)
        else:
            new_doc = DocumentoXML(
                id=uuid.uuid4(),
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

    # 4. Salvar no banco em lote de forma otimizada
    if new_docs:
        # bulk_save_objects é muito mais rápido que add_all, pois pula o tracking do ORM
        db.bulk_save_objects(new_docs)
    
    try:
        # O commit agora vai salvar os updates e os inserts massivos rapidamente
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

@router.get("/summary")
def get_xml_summary(empresa_id: str, db: Session = Depends(get_db)):
    """
    Returns a summary of XMLs imported for the given company, grouped by month/year.
    """
    from sqlalchemy import func
    from app.models.xml import DocumentoXML
    
    # Use to_char for postgres to group by YYYY-MM
    query = db.query(
        func.to_char(DocumentoXML.data_emissao, 'YYYY-MM').label('mes'),
        func.count(DocumentoXML.id).label('quantidade'),
        func.sum(DocumentoXML.valor_total).label('valor_total')
    ).filter(
        DocumentoXML.empresa_id == empresa_id,
        DocumentoXML.data_emissao.isnot(None)
    ).group_by(
        func.to_char(DocumentoXML.data_emissao, 'YYYY-MM')
    ).order_by(
        func.to_char(DocumentoXML.data_emissao, 'YYYY-MM').desc()
    ).all()
    
    return [
        {
            "mes": row.mes,
            "quantidade": row.quantidade,
            "valor_total": float(row.valor_total) if row.valor_total else 0.0
        } for row in query
    ]

@router.get("/list")
def list_xmls(empresa_id: str, mes: str = None, limit: int = 1000, db: Session = Depends(get_db)):
    """
    Returns a list of XMLs for the given company, optionally filtered by month (YYYY-MM).
    """
    from sqlalchemy import func
    from app.models.xml import DocumentoXML
    
    query = db.query(DocumentoXML).filter(DocumentoXML.empresa_id == empresa_id)
    
    if mes:
        query = query.filter(func.to_char(DocumentoXML.data_emissao, 'YYYY-MM') == mes)
        
    query = query.order_by(DocumentoXML.data_emissao.desc()).limit(limit)
    xmls = query.all()
    
    return [
        {
            "id": str(xml.id),
            "chave_nfe": xml.chave_nfe,
            "cnpj_emitente": xml.cnpj_emitente,
            "cnpj_destinatario": xml.cnpj_destinatario,
            "modelo": xml.modelo,
            "serie": xml.serie,
            "numero": xml.numero,
            "data_emissao": xml.data_emissao.strftime("%d/%m/%Y %H:%M") if xml.data_emissao else None,
            "valor_total": float(xml.valor_total) if xml.valor_total else 0.0,
            "situacao": xml.situacao,
            "origem": xml.origem
        } for xml in xmls
    ]
