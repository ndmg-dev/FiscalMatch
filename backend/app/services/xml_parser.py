import traceback
import xml.etree.ElementTree as etree
from datetime import datetime
from typing import Dict, Any

class XMLParser:
    NAMESPACES = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

    @classmethod
    def parse(cls, file_content: bytes) -> Dict[str, Any]:
        try:
            root = etree.fromstring(file_content)
        except etree.ParseError:
            raise ValueError("Invalid XML content")

        infNFe = root.find('.//ns:infNFe', cls.NAMESPACES)
        if infNFe is None:
            raise ValueError("Not an NF-e model 55 XML (missing infNFe)")

        chave_nfe = infNFe.get('Id', '').replace('NFe', '')
        
        ide = infNFe.find('ns:ide', cls.NAMESPACES)
        if ide is None:
            raise ValueError("Missing ide node")
            
        modelo = ide.findtext('ns:mod', namespaces=cls.NAMESPACES)
        if modelo not in ('55', '65'):
            raise ValueError(f"Unsupported model: {modelo}")

        serie = ide.findtext('ns:serie', namespaces=cls.NAMESPACES)
        numero = ide.findtext('ns:nNF', namespaces=cls.NAMESPACES)
        dhEmi = ide.findtext('ns:dhEmi', namespaces=cls.NAMESPACES)
        
        # parse datetime, example format: 2023-01-01T10:00:00-03:00
        data_emissao = None
        if dhEmi:
            try:
                # remove timezone info for simplicity in MVP by just taking the first 19 chars (YYYY-MM-DDTHH:MM:SS)
                dhEmi_clean = dhEmi[:19]
                data_emissao = datetime.strptime(dhEmi_clean, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass

        emit = infNFe.find('ns:emit', cls.NAMESPACES)
        cnpj_emitente = emit.findtext('ns:CNPJ', namespaces=cls.NAMESPACES) if emit is not None else None

        dest = infNFe.find('ns:dest', cls.NAMESPACES)
        cnpj_destinatario = dest.findtext('ns:CNPJ', namespaces=cls.NAMESPACES) if dest is not None else None

        total = infNFe.find('.//ns:total/ns:ICMSTot', cls.NAMESPACES)
        valor_total = None
        if total is not None:
            vNF = total.findtext('ns:vNF', namespaces=cls.NAMESPACES)
            if vNF:
                valor_total = float(vNF)

        # check situation from protNFe if exists
        situacao = "AUTORIZADA"
        prot = root.find('.//ns:protNFe/ns:infProt', cls.NAMESPACES)
        if prot is not None:
            cStat = prot.findtext('ns:cStat', namespaces=cls.NAMESPACES)
            if cStat == '101':
                situacao = "CANCELADA"
            elif cStat != '100':
                situacao = f"OUTRO_{cStat}"

        return {
            "chave_nfe": chave_nfe,
            "modelo": modelo,
            "serie": serie,
            "numero": int(numero) if numero else 0,
            "cnpj_emitente": cnpj_emitente,
            "cnpj_destinatario": cnpj_destinatario,
            "data_emissao": data_emissao,
            "valor_total": valor_total,
            "situacao": situacao
        }
