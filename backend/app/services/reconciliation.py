from typing import List, Dict, Any
from app.models.sped import DocumentoSped, ArquivoSped
from app.models.xml import DocumentoXML
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import logging

logger = logging.getLogger(__name__)

class ReconciliationService:
    def __init__(self, db: Session, empresa_id: str, periodo: str):
        self.db = db
        self.empresa_id = empresa_id
        self.periodo = periodo

    def run(self) -> List[Dict[str, Any]]:
        logger.info("Iniciando conciliação empresa_id=%s periodo=%s", self.empresa_id, self.periodo)

        from app.models.company import Empresa
        empresa = self.db.query(Empresa).filter(Empresa.id == self.empresa_id).first()
        if not empresa:
            return []

        sped_docs = self.db.query(
            DocumentoSped.id, DocumentoSped.chave_nfe, DocumentoSped.modelo,
            DocumentoSped.serie, DocumentoSped.numero, DocumentoSped.cnpj_part,
            DocumentoSped.ind_oper, DocumentoSped.ind_emit, DocumentoSped.cod_sit, 
            DocumentoSped.valor_doc, DocumentoSped.data_doc
        ).join(
            ArquivoSped, DocumentoSped.arquivo_sped_id == ArquivoSped.id
        ).filter(
            DocumentoSped.empresa_id == self.empresa_id,
            ArquivoSped.periodo == self.periodo,
            DocumentoSped.ind_oper == '0', # Apenas Entradas (Ind_Oper = 0)
            DocumentoSped.ind_emit == '1'  # Apenas Emissão de Terceiros (Ind_Emit = 1)
        ).all()
        
        xml_docs = self.db.query(
            DocumentoXML.id, DocumentoXML.chave_nfe, DocumentoXML.modelo,
            DocumentoXML.serie, DocumentoXML.numero, DocumentoXML.cnpj_emitente,
            DocumentoXML.cnpj_destinatario, DocumentoXML.situacao, DocumentoXML.valor_total, DocumentoXML.data_emissao
        ).filter(
            DocumentoXML.empresa_id == self.empresa_id,
            func.to_char(DocumentoXML.data_emissao, 'YYYY-MM') == self.periodo,
        ).all()

        # O(1) hash maps for SPED
        sped_by_chave = {}
        sped_by_composite = {}
        for s in sped_docs:
            if s.cod_sit in ('02', '03', '04', '05'):
                continue # ignore canceled SPED
            if s.chave_nfe:
                sped_by_chave[s.chave_nfe] = s
            
            # composite key: (modelo, serie, numero, cnpj_part)
            serie_int = int(s.serie) if s.serie and s.serie.isdigit() else s.serie
            comp_key = (s.modelo, serie_int, s.numero, s.cnpj_part)
            sped_by_composite[comp_key] = s

        results = []

        for xml in xml_docs:
            if xml.situacao == "CANCELADA":
                continue # Ignora XMLs cancelados na base

            if xml.modelo not in ('55', '65'):
                continue

            # Find match O(1) in SPED
            matched_sped = None
            if xml.chave_nfe and xml.chave_nfe in sped_by_chave:
                matched_sped = sped_by_chave[xml.chave_nfe]
            else:
                # Fallback match
                serie_int = int(xml.serie) if xml.serie and xml.serie.isdigit() else xml.serie
                comp_key = (xml.modelo, serie_int, xml.numero, xml.cnpj_emitente)
                if comp_key in sped_by_composite:
                    matched_sped = sped_by_composite[comp_key]
            
            if not matched_sped:
                # Usuário solicitou que o relatório acuse SOMENTE o que foi encontrado no SPED,
                # para que não fiquem "milhares de itens faltosos acusados na interface" (XMLs de saída/lixo)
                continue
            else:
                diffs = self._compare(matched_sped, xml)
                if diffs:
                    results.append(self._build_result("OK", matched_sped, xml, "Conciliado com divergências", diffs))
                else:
                    results.append(self._build_result("OK", matched_sped, xml, "Escriturado corretamente no SPED"))

        logger.info(
            "Conciliação finalizada empresa_id=%s periodo=%s: %d resultados",
            self.empresa_id, self.periodo, len(results)
        )
        return results

    def _compare(self, sped: DocumentoSped, xml: DocumentoXML) -> Dict[str, Any]:
        diffs = {}
        if sped.valor_doc is not None and xml.valor_total is not None:
            if abs(float(sped.valor_doc) - float(xml.valor_total)) > 0.10: # 10 cents tolerance
                diffs["valor"] = {"sped": float(sped.valor_doc), "xml": float(xml.valor_total)}
        
        if sped.data_doc and xml.data_emissao:
            if sped.data_doc.date() != xml.data_emissao.date():
                diffs["data_emissao"] = {"sped": sped.data_doc.strftime("%Y-%m-%d"), "xml": xml.data_emissao.strftime("%Y-%m-%d")}

        return diffs

    def _build_result(self, status: str, sped: DocumentoSped, xml: DocumentoXML, obs: str, diffs: Dict = None) -> Dict[str, Any]:
        return {
            "status": status,
            "documento_sped_id": sped.id if sped else None,
            "documento_fiscal_id": xml.id if xml else None,
            "observacao": obs,
            "diferencas_json": diffs
        }
