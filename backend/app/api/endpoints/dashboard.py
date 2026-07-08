from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.core.database import get_db
from app.models.company import Empresa
from app.models.xml import DocumentoXML
from app.models.sped import DocumentoSped, ArquivoSped
from app.models.reconciliation import Conciliacao

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_empresas = db.query(func.count(Empresa.id)).scalar() or 0
    total_xmls = db.query(func.count(DocumentoXML.id)).scalar() or 0
    total_sped_docs = db.query(func.count(DocumentoSped.id)).scalar() or 0
    total_conciliacoes = db.query(func.count(Conciliacao.id)).scalar() or 0

    # Status breakdown
    status_counts = dict(
        db.query(Conciliacao.status, func.count(Conciliacao.id))
        .group_by(Conciliacao.status)
        .all()
    )

    ok_count = status_counts.get("OK", 0)
    faltante_count = status_counts.get("FALTANTE", 0)
    divergente_count = status_counts.get("DIVERGENTE", 0)
    nao_atribuida_count = status_counts.get("NAO_ATRIBUIDA", 0)
    ignorada_count = status_counts.get("IGNORADA_POR_REGRA", 0)

    # Tax compliance rate
    actionable = ok_count + faltante_count + divergente_count + nao_atribuida_count
    compliance_rate = round((ok_count / actionable) * 100, 1) if actionable > 0 else 0

    # Attention ranking: get all groupings and sort by worst compliance
    attention_raw = (
        db.query(
            Conciliacao.empresa_id,
            Conciliacao.periodo,
            Empresa.razao_social,
            func.count(Conciliacao.id).label("total"),
            func.sum(case((Conciliacao.status == 'OK', 1), else_=0)).label("ok"),
            func.sum(case((Conciliacao.status == 'FALTANTE', 1), else_=0)).label("faltante"),
            func.sum(case((Conciliacao.status == 'DIVERGENTE', 1), else_=0)).label("divergente"),
            func.max(Conciliacao.created_at).label("last_run"),
        )
        .join(Empresa, Conciliacao.empresa_id == Empresa.id)
        .group_by(Conciliacao.empresa_id, Conciliacao.periodo, Empresa.razao_social)
        .all()
    )

    attention_list = []
    for r in attention_raw:
        ok = int(r.ok) if r.ok else 0
        faltante = int(r.faltante) if r.faltante else 0
        divergente = int(r.divergente) if r.divergente else 0
        total = ok + faltante + divergente
        
        # Calculate a penalty score (more missing/divergent = higher score)
        # We also consider compliance rate
        compliance = (ok / total) if total > 0 else 1.0
        penalty_score = (faltante + divergente) * (1 - compliance)
        
        # Only add to attention list if there is a problem
        if (faltante + divergente) > 0:
            attention_list.append({
                "empresa_id": str(r.empresa_id),
                "empresa_nome": r.razao_social,
                "periodo": r.periodo,
                "total": r.total,
                "ok": ok,
                "faltante": faltante,
                "divergente": divergente,
                "last_run": r.last_run.isoformat() if r.last_run else None,
                "penalty_score": penalty_score,
                "compliance_rate": round(compliance * 100, 1)
            })

    # Sort by highest penalty score, keep top 10
    attention_list.sort(key=lambda x: x["penalty_score"], reverse=True)
    recent = attention_list[:10]

    # Empresas list with counts — single query using subqueries
    xml_subq = db.query(DocumentoXML.empresa_id, func.count(DocumentoXML.id).label('xml_count')).group_by(DocumentoXML.empresa_id).subquery()
    sped_subq = db.query(DocumentoSped.empresa_id, func.count(DocumentoSped.id).label('sped_count')).group_by(DocumentoSped.empresa_id).subquery()

    empresas_with_counts = db.query(
        Empresa.id, Empresa.razao_social, Empresa.cnpj,
        func.coalesce(xml_subq.c.xml_count, 0).label('xml_count'),
        func.coalesce(sped_subq.c.sped_count, 0).label('sped_count')
    ).outerjoin(xml_subq, Empresa.id == xml_subq.c.empresa_id
    ).outerjoin(sped_subq, Empresa.id == sped_subq.c.empresa_id
    ).all()

    empresas_list = []
    for e in empresas_with_counts:
        empresas_list.append({
            "id": str(e.id),
            "razao_social": e.razao_social,
            "cnpj": e.cnpj,
            "xml_count": e.xml_count,
            "sped_count": e.sped_count,
        })

    return {
        "total_empresas": total_empresas,
        "total_xmls": total_xmls,
        "total_sped_docs": total_sped_docs,
        "total_conciliacoes": total_conciliacoes,
        "compliance_rate": compliance_rate,
        "status_breakdown": {
            "OK": ok_count,
            "FALTANTE": faltante_count,
            "DIVERGENTE": divergente_count,
            "NAO_ATRIBUIDA": nao_atribuida_count,
            "IGNORADA_POR_REGRA": ignorada_count,
        },
        "recent_reconciliations": recent,
        "empresas": empresas_list,
    }
