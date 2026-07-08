from typing import List, Dict, Any
from app.models.sped import DocumentoSped
from app.models.xml import DocumentoXML
from sqlalchemy.orm import Session
import json

class ReconciliationService:
    def __init__(self, db: Session, empresa_id: str, periodo: str):
        self.db = db
        self.empresa_id = empresa_id
        self.periodo = periodo

    def run(self) -> List[Dict[str, Any]]:
        from app.models.sped import ArquivoSped
        sped_docs = self.db.query(
            DocumentoSped.id, DocumentoSped.chave_nfe, DocumentoSped.modelo,
            DocumentoSped.serie, DocumentoSped.numero, DocumentoSped.cnpj_part,
            DocumentoSped.ind_oper, DocumentoSped.cod_sit, DocumentoSped.valor_doc,
            DocumentoSped.data_doc
        ).join(
            ArquivoSped, DocumentoSped.arquivo_sped_id == ArquivoSped.id
        ).filter(
            DocumentoSped.empresa_id == self.empresa_id,
            ArquivoSped.periodo == self.periodo
        ).yield_per(5000)
        
        xml_docs = self.db.query(
            DocumentoXML.id, DocumentoXML.chave_nfe, DocumentoXML.modelo,
            DocumentoXML.serie, DocumentoXML.numero, DocumentoXML.cnpj_emitente,
            DocumentoXML.situacao, DocumentoXML.valor_total, DocumentoXML.data_emissao
        ).filter(
            DocumentoXML.empresa_id == self.empresa_id,
        ).all()

        # O(1) hash maps for XMLs
        xml_by_chave = {}
        xml_by_composite = {}
        for x in xml_docs:
            if x.chave_nfe:
                xml_by_chave[x.chave_nfe] = x
            
            # composite key: (modelo, serie, numero, cnpj_emitente)
            # serie em int para evitar problemas de formatação ('001' vs '1')
            serie_int = int(x.serie) if x.serie and x.serie.isdigit() else x.serie
            comp_key = (x.modelo, serie_int, x.numero, x.cnpj_emitente)
            xml_by_composite[comp_key] = x

        results = []
        xml_matched = set()

        for sped in sped_docs:
            if sped.modelo not in ('55', '65'):
                results.append(self._build_result("IGNORADA_POR_REGRA", sped, None, "Modelo ignorado no MVP"))
                continue

            if sped.cod_sit in ('02', '03', '04', '05'):
                results.append(self._build_result("IGNORADA_POR_REGRA", sped, None, "Documento cancelado/inutilizado no SPED"))
                continue

            # Find match O(1)
            matched_xml = None
            if sped.chave_nfe and sped.chave_nfe in xml_by_chave:
                matched_xml = xml_by_chave[sped.chave_nfe]
            else:
                # Fallback match
                serie_int = int(sped.serie) if sped.serie and sped.serie.isdigit() else sped.serie
                if sped.ind_oper == '0': # Entrada, emitente é o terceiro
                    comp_key = (sped.modelo, serie_int, sped.numero, sped.cnpj_part)
                else: # Saída, emitente é a empresa
                    comp_key = (sped.modelo, serie_int, sped.numero, None) # Ideally we need the company CNPJ here, but since xml_docs is already filtered by empresa_id, we can check if it exists with company CNPJ
                    # We need the company CNPJ. Let's find it from the first XML if available, or pass it.
                    # Actually, if ind_oper == 1, the emitente in XML is the company itself.
                    # We can search the dict for any key that matches (modelo, serie, numero) where emitente is NOT a third party.
                    # Let's simplify for O(1) by assuming the fallback must be exact.
                    pass 
                
                if 'comp_key' in locals() and comp_key in xml_by_composite:
                    matched_xml = xml_by_composite[comp_key]
                elif sped.ind_oper == '1':
                    # Find by scanning just once (rare fallback)
                    for k, v in xml_by_composite.items():
                        if k[0] == sped.modelo and k[1] == serie_int and k[2] == sped.numero:
                            matched_xml = v
                            break
            
            if not matched_xml:
                results.append(self._build_result("FALTANTE", sped, None, "XML não encontrado"))
            else:
                xml_matched.add(matched_xml.id)
                diffs = self._compare(sped, matched_xml)
                if diffs:
                    results.append(self._build_result("DIVERGENTE", sped, matched_xml, "Diferenças nos valores ou metadados", diffs))
                else:
                    results.append(self._build_result("OK", sped, matched_xml, "Conciliado com sucesso"))

        for xml in xml_docs:
            if xml.id not in xml_matched:
                if xml.situacao == "CANCELADA":
                    results.append(self._build_result("IGNORADA_POR_REGRA", None, xml, "XML cancelado"))
                elif xml.modelo not in ('55', '65'):
                    results.append(self._build_result("IGNORADA_POR_REGRA", None, xml, "Modelo ignorado no MVP"))
                else:
                    results.append(self._build_result("NAO_ATRIBUIDA", None, xml, "Sem registro correspondente no SPED"))

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
