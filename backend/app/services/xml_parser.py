import traceback
import xml.etree.ElementTree as etree
from datetime import datetime
from typing import Dict, Any
import re

class XMLParser:
    @classmethod
    def parse(cls, file_content: bytes) -> Dict[str, Any]:
        try:
            root = etree.fromstring(file_content)
        except etree.ParseError:
            try:
                # Fallback: attempt to decode as ISO-8859-1, fix XML declaration, and re-parse
                text = file_content.decode('iso-8859-1')
                text = re.sub(r'encoding="[^"]+"', 'encoding="UTF-8"', text)
                root = etree.fromstring(text.encode('utf-8'))
            except Exception:
                raise ValueError("Invalid XML content")

        # Strip all namespaces from tags for robust searching
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]

        # Check if it's an Event XML (like a cancellation)
        if root.tag == 'procEventoNFe' or root.find('.//procEventoNFe') is not None:
            tpEvento = root.find('.//tpEvento')
            if tpEvento is not None and tpEvento.text in ('110111', '110112', '110113'):
                chNFe = root.find('.//chNFe')
                if chNFe is not None:
                    return {
                        "chave_nfe": chNFe.text,
                        "modelo": None,
                        "serie": None,
                        "numero": None,
                        "cnpj_emitente": None,
                        "cnpj_destinatario": None,
                        "data_emissao": None,
                        "valor_total": None,
                        "situacao": "CANCELADA",
                        "is_evento": True
                    }

        infNFe = root.find('.//infNFe')
        if infNFe is None:
            raise ValueError("Not an NF-e model 55/65 XML (missing infNFe tag)")

        chave_nfe = infNFe.get('Id', '').replace('NFe', '')
        if not chave_nfe:
            raise ValueError("Missing Id attribute in infNFe")
            
        ide = infNFe.find('ide')
        if ide is None:
            raise ValueError("Missing ide node")
            
        modelo = ide.findtext('mod')
        if modelo not in ('55', '65'):
            raise ValueError(f"Unsupported model: {modelo}")

        serie = ide.findtext('serie')
        numero = ide.findtext('nNF')
        dhEmi = ide.findtext('dhEmi')
        
        # parse datetime, example format: 2023-01-01T10:00:00-03:00
        data_emissao = None
        if dhEmi:
            try:
                # remove timezone info for simplicity in MVP by just taking the first 19 chars (YYYY-MM-DDTHH:MM:SS)
                dhEmi_clean = dhEmi[:19]
                data_emissao = datetime.strptime(dhEmi_clean, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass

        emit = infNFe.find('emit')
        cnpj_emitente = None
        if emit is not None:
            cnpj_emitente = emit.findtext('CNPJ')
            if not cnpj_emitente:
                cnpj_emitente = emit.findtext('CPF')
                


        dest = infNFe.find('dest')
        cnpj_destinatario = None
        if dest is not None:
            cnpj_destinatario = dest.findtext('CNPJ')
            if not cnpj_destinatario:
                cnpj_destinatario = dest.findtext('CPF')

        total = infNFe.find('.//total/ICMSTot')
        valor_total = None
        if total is not None:
            vNF = total.findtext('vNF')
            if vNF:
                valor_total = float(vNF)

        # check situation from protNFe if exists
        situacao = "AUTORIZADA"
        prot = root.find('.//protNFe/infProt')
        if prot is not None:
            cStat = prot.findtext('cStat')
            if cStat == '101':
                situacao = "CANCELADA"
            elif cStat != '100':
                situacao = f"OUTRO_{cStat}"

        return {
            "chave_nfe": chave_nfe,
            "modelo": modelo,
            "serie": serie,
            "numero": int(numero) if numero else None,
            "cnpj_emitente": cnpj_emitente,
            "cnpj_destinatario": cnpj_destinatario,
            "data_emissao": data_emissao,
            "valor_total": valor_total,
            "situacao": situacao
        }
