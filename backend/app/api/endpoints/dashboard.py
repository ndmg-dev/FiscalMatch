from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
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

    from sqlalchemy import case
    # Attention ranking: get all groupings and sort by worst compliance
    attention_raw = (
        db.query(
            Conciliacao.empresa_id,
            Conciliacao.periodo,
            func.count(Conciliacao.id).label("total"),
            func.sum(case((Conciliacao.status == 'OK', 1), else_=0)).label("ok"),
            func.sum(case((Conciliacao.status == 'FALTANTE', 1), else_=0)).label("faltante"),
            func.sum(case((Conciliacao.status == 'DIVERGENTE', 1), else_=0)).label("divergente"),
            func.max(Conciliacao.created_at).label("last_run"),
        )
        .group_by(Conciliacao.empresa_id, Conciliacao.periodo)
        .all()
    )

    attention_list = []
    for r in attention_raw:
        empresa = db.query(Empresa).filter(Empresa.id == r.empresa_id).first()
        
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
                "empresa_nome": empresa.razao_social if empresa else "Desconhecida",
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

    # Empresas list with counts
    empresas = db.query(Empresa).all()
    empresas_list = []
    for e in empresas:
        xml_count = db.query(func.count(DocumentoXML.id)).filter(DocumentoXML.empresa_id == e.id).scalar() or 0
        sped_count = db.query(func.count(DocumentoSped.id)).filter(DocumentoSped.empresa_id == e.id).scalar() or 0
        empresas_list.append({
            "id": str(e.id),
            "razao_social": e.razao_social,
            "cnpj": e.cnpj,
            "xml_count": xml_count,
            "sped_count": sped_count,
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
