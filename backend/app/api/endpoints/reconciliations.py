from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.company import Empresa
from app.models.reconciliation import Conciliacao
from app.services.reconciliation import ReconciliationService
from app.services.exporter import ExporterService
import json

router = APIRouter()

@router.get("/{empresa_id}/historico")
def get_historico(empresa_id: str, db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    # Query to group reconciliations by period for this company
    recent_raw = (
        db.query(
            Conciliacao.periodo,
            func.count(Conciliacao.id).label("total"),
            func.max(Conciliacao.created_at).label("last_run"),
        )
        .filter(Conciliacao.empresa_id == empresa_id)
        .group_by(Conciliacao.periodo)
        .order_by(func.max(Conciliacao.created_at).desc())
        .all()
    )

    history = []
    for r in recent_raw:
        # Get status breakdown for this specific period
        statuses = dict(
            db.query(Conciliacao.status, func.count(Conciliacao.id))
            .filter(Conciliacao.empresa_id == empresa_id, Conciliacao.periodo == r.periodo)
            .group_by(Conciliacao.status)
            .all()
        )
        history.append({
            "periodo": r.periodo,
            "total": r.total,
            "ok": statuses.get("OK", 0),
            "faltante": statuses.get("FALTANTE", 0),
            "divergente": statuses.get("DIVERGENTE", 0),
            "ignorada": statuses.get("IGNORADA_POR_REGRA", 0),
            "nao_atribuida": statuses.get("NAO_ATRIBUIDA", 0),
            "last_run": r.last_run.isoformat() if r.last_run else None,
        })
        
    return history

@router.post("")
def run_reconciliation(empresa_id: str, periodo: str, sync_sieg: bool = False, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if sync_sieg:
        from app.services.sieg_connector import SiegConnector
        from app.services.xml_parser import XMLParser
        from app.models.xml import DocumentoXML
        import base64
        
        sieg = SiegConnector()
        sieg_result = sieg.sync_documents(empresa.cnpj, periodo)
        
        if sieg_result.get("status") == "error":
            raise HTTPException(status_code=400, detail=sieg_result.get("message", "Erro na API da SIEG"))
        
        if sieg_result.get("status") == "success":
            for xml_b64 in sieg_result.get("xmls", []):
                try:
                    xml_bytes = base64.b64decode(xml_b64)
                    parsed = XMLParser.parse(xml_bytes)
                    
                    # Upsert by chave_nfe
                    existing = db.query(DocumentoXML).filter(DocumentoXML.chave_nfe == parsed["chave_nfe"]).first()
                    if existing:
                        for k, v in parsed.items():
                            setattr(existing, k, v)
                        existing.origem = "SIEG"
                    else:
                        new_xml = DocumentoXML(
                            empresa_id=empresa_id,
                            origem="SIEG",
                            **parsed
                        )
                        db.add(new_xml)
                except Exception as e:
                    print(f"Erro ao parsear XML do Sieg: {e}")
            db.commit()

    # Clear previous reconciliations for the period
    db.query(Conciliacao).filter(
        Conciliacao.empresa_id == empresa_id,
        Conciliacao.periodo == periodo
    ).delete()
    db.commit()

    # Run synchronously for MVP simplicity, or could be enqueued
    svc = ReconciliationService(db, empresa_id, periodo)
    results = svc.run()

    docs_to_insert = []
    for r in results:
        docs_to_insert.append(Conciliacao(
            empresa_id=empresa_id,
            periodo=periodo,
            **r
        ))
    if docs_to_insert:
        db.bulk_save_objects(docs_to_insert)
    db.commit()

    warning = None
    if sync_sieg and 'sieg_result' in locals():
        if sieg_result.get("downloaded_count", 0) == 0 and "Nenhum documento" in sieg_result.get("message", ""):
            warning = "Nenhum XML foi localizado na SIEG. Verifique se o Certificado A1 está cadastrado no painel deles."

    return {"message": "Conciliação executada com sucesso", "total_registros": len(results), "warning": warning}

@router.get("/{empresa_id}/{periodo}/relatorio")
def get_relatorio(empresa_id: str, periodo: str, status: str = None, limit: int = None, db: Session = Depends(get_db)):
    from app.models.xml import DocumentoXML
    from app.models.sped import DocumentoSped
    
    query = db.query(Conciliacao, DocumentoXML, DocumentoSped)\
        .outerjoin(DocumentoXML, Conciliacao.documento_fiscal_id == DocumentoXML.id)\
        .outerjoin(DocumentoSped, Conciliacao.documento_sped_id == DocumentoSped.id)\
        .filter(
            Conciliacao.empresa_id == empresa_id,
            Conciliacao.periodo == periodo
        )
        
    if status and status != 'ALL':
        query = query.filter(Conciliacao.status == status)
        
    # Order by status, then created_at to have a consistent order
    query = query.order_by(Conciliacao.status.desc(), Conciliacao.created_at.desc())
        
    if limit is not None:
        query = query.limit(limit)
        
    records = query.all()
    
    report = []
    for r, xml, sped in records:
        report.append({
            "id": str(r.id),
            "status": r.status,
            "chave_nfe": xml.chave_nfe if xml else (sped.chave_nfe if sped else None),
            "cnpj_emitente": xml.cnpj_emitente if xml else (sped.cnpj_part if sped else None),
            "cnpj_destinatario": xml.cnpj_destinatario if xml else None,
            "nome_participante": sped.nome_part if sped else None,
            "modelo": xml.modelo if xml else (sped.modelo if sped else None),
            "serie": xml.serie if xml else (sped.serie if sped else None),
            "numero": xml.numero if xml else (sped.numero if sped else None),
            "data_emissao": xml.data_emissao.strftime("%d/%m/%Y") if xml and xml.data_emissao else (sped.data_doc.strftime("%d/%m/%Y") if sped and sped.data_doc else None),
            "data_entrada_saida": sped.data_entrada_saida.strftime("%d/%m/%Y") if sped and sped.data_entrada_saida else None,
            "valor_xml": float(xml.valor_total) if xml and xml.valor_total else None,
            "valor_sped": float(sped.valor_doc) if sped and sped.valor_doc else None,
            "diferenca": r.diferencas_json,
            "situacao_nota": xml.situacao if xml else (sped.cod_sit if sped else None),
            "origem_documento": xml.origem if xml else None,
            "observacao": r.observacao
        })
        
    return report

@router.get("/{empresa_id}/{periodo}/exportar.xlsx")
def export_excel(empresa_id: str, periodo: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    import openpyxl, tempfile, json, os
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.close()
    
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("Conciliacao")
    
    headers = [
        "Status da conciliação", "Chave da NF-e", "CNPJ emitente", "CNPJ destinatário",
        "Nome do participante", "Modelo", "Série", "Número", "Data de emissão",
        "Data de entrada/saída", "Valor no XML", "Valor no SPED", "Diferença",
        "Situação da nota", "Origem do documento", "Observação do sistema"
    ]
    ws.append(headers)
    
    for row in get_relatorio_stream(empresa_id, periodo, db):
        diferenca = row.get("diferenca")
        if isinstance(diferenca, dict) or isinstance(diferenca, list):
            diferenca = json.dumps(diferenca, ensure_ascii=False)
            
        ws.append([
            row.get("status"), row.get("chave_nfe"), row.get("cnpj_emitente"), row.get("cnpj_destinatario"),
            row.get("nome_participante"), row.get("modelo"), row.get("serie"), row.get("numero"),
            row.get("data_emissao"), row.get("data_entrada_saida"), row.get("valor_xml"),
            row.get("valor_sped"), diferenca, row.get("situacao_nota"),
            row.get("origem_documento"), row.get("observacao")
        ])
        
    wb.save(tmp.name)
    background_tasks.add_task(os.remove, tmp.name)
    
    return FileResponse(
        path=tmp.name, 
        filename=f"conciliacao_{periodo}.xlsx", 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def get_relatorio_stream(empresa_id: str, periodo: str, db: Session):
    from app.models.xml import DocumentoXML
    from app.models.sped import DocumentoSped
    
    query = db.query(
        Conciliacao.id, Conciliacao.status, Conciliacao.diferencas_json, Conciliacao.observacao,
        DocumentoXML.chave_nfe.label("xml_chave_nfe"), DocumentoXML.cnpj_emitente.label("xml_cnpj_emitente"),
        DocumentoXML.cnpj_destinatario.label("xml_cnpj_destinatario"), DocumentoXML.modelo.label("xml_modelo"),
        DocumentoXML.serie.label("xml_serie"), DocumentoXML.numero.label("xml_numero"),
        DocumentoXML.data_emissao.label("xml_data_emissao"), DocumentoXML.valor_total.label("xml_valor_total"),
        DocumentoXML.situacao.label("xml_situacao"), DocumentoXML.origem.label("xml_origem"),
        DocumentoSped.chave_nfe.label("sped_chave_nfe"), DocumentoSped.cnpj_part.label("sped_cnpj_part"),
        DocumentoSped.nome_part.label("sped_nome_part"), DocumentoSped.modelo.label("sped_modelo"),
        DocumentoSped.serie.label("sped_serie"), DocumentoSped.numero.label("sped_numero"),
        DocumentoSped.data_doc.label("sped_data_doc"), DocumentoSped.data_entrada_saida.label("sped_data_es"),
        DocumentoSped.valor_doc.label("sped_valor_doc"), DocumentoSped.cod_sit.label("sped_cod_sit")
    )\
        .outerjoin(DocumentoXML, Conciliacao.documento_fiscal_id == DocumentoXML.id)\
        .outerjoin(DocumentoSped, Conciliacao.documento_sped_id == DocumentoSped.id)\
        .filter(
            Conciliacao.empresa_id == empresa_id,
            Conciliacao.periodo == periodo
        )
        
    for row in query.yield_per(2000):
        yield {
            "status": row.status,
            "chave_nfe": row.xml_chave_nfe or row.sped_chave_nfe,
            "cnpj_emitente": row.xml_cnpj_emitente or row.sped_cnpj_part,
            "cnpj_destinatario": row.xml_cnpj_destinatario,
            "nome_participante": row.sped_nome_part,
            "modelo": row.xml_modelo or row.sped_modelo,
            "serie": row.xml_serie or row.sped_serie,
            "numero": row.xml_numero or row.sped_numero,
            "data_emissao": row.xml_data_emissao.strftime("%d/%m/%Y") if row.xml_data_emissao else (row.sped_data_doc.strftime("%d/%m/%Y") if row.sped_data_doc else None),
            "data_entrada_saida": row.sped_data_es.strftime("%d/%m/%Y") if row.sped_data_es else None,
            "valor_xml": float(row.xml_valor_total) if row.xml_valor_total else None,
            "valor_sped": float(row.sped_valor_doc) if row.sped_valor_doc else None,
            "diferenca": row.diferencas_json,
            "situacao_nota": row.xml_situacao or row.sped_cod_sit,
            "origem_documento": row.xml_origem,
            "observacao": row.observacao
        }

@router.get("/{empresa_id}/{periodo}/exportar.csv")
def export_csv(empresa_id: str, periodo: str, db: Session = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    import csv, io, json
    
    def iter_csv():
        output = io.StringIO()
        headers = [
            "Status da conciliação", "Chave da NF-e", "CNPJ emitente", "CNPJ destinatário",
            "Nome do participante", "Modelo", "Série", "Número", "Data de emissão",
            "Data de entrada/saída", "Valor no XML", "Valor no SPED", "Diferença",
            "Situação da nota", "Origem do documento", "Observação do sistema"
        ]
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        
        for row in get_relatorio_stream(empresa_id, periodo, db):
            diferenca = row.get("diferenca")
            if isinstance(diferenca, dict) or isinstance(diferenca, list):
                diferenca = json.dumps(diferenca, ensure_ascii=False)
                
            mapped_row = {
                "Status da conciliação": row.get("status"),
                "Chave da NF-e": row.get("chave_nfe"),
                "CNPJ emitente": row.get("cnpj_emitente"),
                "CNPJ destinatário": row.get("cnpj_destinatario"),
                "Nome do participante": row.get("nome_participante"),
                "Modelo": row.get("modelo"),
                "Série": row.get("serie"),
                "Número": row.get("numero"),
                "Data de emissão": row.get("data_emissao"),
                "Data de entrada/saída": row.get("data_entrada_saida"),
                "Valor no XML": row.get("valor_xml"),
                "Valor no SPED": row.get("valor_sped"),
                "Diferença": diferenca,
                "Situação da nota": row.get("situacao_nota"),
                "Origem do documento": row.get("origem_documento"),
                "Observação do sistema": row.get("observacao"),
            }
            writer.writerow(mapped_row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            
    headers = {'Content-Disposition': f'attachment; filename="conciliacao_{periodo}.csv"'}
    return StreamingResponse(iter_csv(), headers=headers, media_type='text/csv')

@router.get("/{empresa_id}/auditoria/xml")
def auditoria_xml(empresa_id: str, mes: str, db: Session = Depends(get_db)):
    """
    Relatório Reverso: Busca todos os XMLs de um determinado mês e verifica
    em quais períodos do SPED eles foram efetivamente escriturados.
    """
    from sqlalchemy import func
    from app.models.xml import DocumentoXML
    
    # Busca todos os XMLs emitidos no mês
    xmls = db.query(DocumentoXML).filter(
        DocumentoXML.empresa_id == empresa_id,
        func.to_char(DocumentoXML.data_emissao, 'YYYY-MM') == mes
    ).all()
    
    # Para cada XML, vamos ver se ele tem alguma conciliação com documento_sped_id não nulo
    xml_ids = [xml.id for xml in xmls]
    
    conciliacoes = db.query(Conciliacao).filter(
        Conciliacao.documento_fiscal_id.in_(xml_ids),
        Conciliacao.documento_sped_id.isnot(None)
    ).all()
    
    # Agrupa períodos escriturados por XML
    escriturados_map = {}
    for c in conciliacoes:
        if c.documento_fiscal_id not in escriturados_map:
            escriturados_map[c.documento_fiscal_id] = []
        if c.periodo not in escriturados_map[c.documento_fiscal_id]:
            escriturados_map[c.documento_fiscal_id].append({
                "periodo": c.periodo,
                "status": c.status
            })
            
    report = []
    for xml in xmls:
        speds_encontrados = escriturados_map.get(xml.id, [])
        
        report.append({
            "id": str(xml.id),
            "chave_nfe": xml.chave_nfe,
            "numero": xml.numero,
            "serie": xml.serie,
            "data_emissao": xml.data_emissao.strftime("%d/%m/%Y %H:%M") if xml.data_emissao else None,
            "valor": float(xml.valor_total) if xml.valor_total else 0.0,
            "situacao_sefaz": xml.situacao,
            "escriturado": len(speds_encontrados) > 0,
            "speds_encontrados": speds_encontrados
        })
        
    return {
        "mes": mes,
        "total_xmls": len(xmls),
        "total_escriturados": sum(1 for r in report if r["escriturado"]),
        "total_nao_escriturados": sum(1 for r in report if not r["escriturado"]),
        "detalhes": report
    }
