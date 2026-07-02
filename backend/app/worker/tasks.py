from app.core.database import SessionLocal
from app.core.storage import storage
from app.models.sped import ArquivoSped, DocumentoSped
from app.models.xml import DocumentoXML
from app.models.log import LogProcessamento
from app.services.sped_parser import SpedParser
from app.services.xml_parser import XMLParser
import traceback

def process_sped_file(arquivo_sped_id: str):
    db = SessionLocal()
    try:
        arquivo = db.query(ArquivoSped).filter(ArquivoSped.id == arquivo_sped_id).first()
        if not arquivo:
            return
        
        arquivo.status = "PARSING"
        db.commit()

        # Download from storage
        file_bytes = storage.get_file(arquivo.storage_path)
        content = file_bytes.decode('windows-1252', errors='replace') # SPED is usually windows-1252 or utf-8

        parser = SpedParser()
        result = parser.parse(content)

        # Clear old docs for this file if reprocessing
        db.query(DocumentoSped).filter(DocumentoSped.arquivo_sped_id == arquivo.id).delete()

        # Insert new ones
        docs_to_insert = []
        for doc in result["documents"]:
            docs_to_insert.append(DocumentoSped(
                arquivo_sped_id=arquivo.id,
                empresa_id=arquivo.empresa_id,
                **doc
            ))
        
        if docs_to_insert:
            db.bulk_save_objects(docs_to_insert)

        arquivo.status = "COMPLETED"
        db.add(LogProcessamento(empresa_id=arquivo.empresa_id, tipo="PARSE_SPED", status="SUCCESS", mensagem=f"Sped processado: {len(docs_to_insert)} registros C100"))
        db.commit()

    except Exception as e:
        if arquivo:
            arquivo.status = "ERROR"
            db.add(LogProcessamento(empresa_id=arquivo.empresa_id, tipo="PARSE_SPED", status="ERROR", mensagem="Erro ao processar SPED", detalhes=traceback.format_exc()))
            db.commit()
    finally:
        db.close()

def process_xml_file(empresa_id: str, storage_path: str, origem: str):
    db = SessionLocal()
    try:
        file_bytes = storage.get_file(storage_path)
        result = XMLParser.parse(file_bytes)

        # Upsert by chave_nfe
        existing = db.query(DocumentoXML).filter(DocumentoXML.chave_nfe == result["chave_nfe"]).first()
        if existing:
            for k, v in result.items():
                setattr(existing, k, v)
            existing.origem = origem
            existing.storage_path = storage_path
        else:
            new_xml = DocumentoXML(
                empresa_id=empresa_id,
                origem=origem,
                storage_path=storage_path,
                **result
            )
            db.add(new_xml)
        
        db.commit()
    except Exception as e:
        db.add(LogProcessamento(empresa_id=empresa_id, tipo="PARSE_XML", status="ERROR", mensagem=f"Erro ao processar XML: {storage_path}", detalhes=traceback.format_exc()))
        db.commit()
    finally:
        db.close()
