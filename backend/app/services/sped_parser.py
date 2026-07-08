import io
from datetime import datetime
from typing import Dict, List, Any, Optional

class SpedParser:
    def __init__(self):
        self.participants: Dict[str, Dict[str, str]] = {}
        self.documents: List[Dict[str, Any]] = []
        self.periodo: Optional[str] = None
        self.empresa_cnpj: Optional[str] = None

    def parse_stream(self, lines_iterable):
        for idx, line in enumerate(lines_iterable):
            if isinstance(line, bytes):
                line = line.decode('windows-1252', errors='replace')
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) < 2:
                continue
            
            reg = parts[1]
            
            if reg == '0000':
                self._parse_0000(parts)
            elif reg == '0150':
                self._parse_0150(parts)
            elif reg == 'C100':
                doc = self._parse_c100(parts, idx + 1)
                if doc:
                    # Resolve participant details immediately
                    cod_part = doc.get("cod_part")
                    if cod_part and cod_part in self.participants:
                        part = self.participants[cod_part]
                        doc["nome_part"] = part.get("nome")
                        doc["cnpj_part"] = part.get("cnpj")
                    yield doc

    def _parse_0000(self, parts: List[str]):
        if len(parts) > 5:
            dt_ini = parts[4]
            if len(dt_ini) == 8:
                self.periodo = f"{dt_ini[4:8]}-{dt_ini[2:4]}"
        if len(parts) > 8:
            self.empresa_cnpj = parts[8]

    def _parse_0150(self, parts: List[str]):
        if len(parts) > 5:
            cod_part = parts[2]
            nome = parts[3]
            cnpj = parts[5]
            self.participants[cod_part] = {"nome": nome, "cnpj": cnpj}

    def _parse_c100(self, parts: List[str], linha: int):
        if len(parts) < 13:
            return
        
        ind_oper = parts[2]
        ind_emit = parts[3]
        cod_part = parts[4]
        modelo = parts[5]
        cod_sit = parts[6]
        serie = parts[7]
        numero = parts[8]
        chave_nfe = parts[9]
        dt_doc_str = parts[10]
        dt_e_s_str = parts[11]
        vl_doc_str = parts[12]

        def parse_date(d_str):
            if not d_str or len(d_str) != 8:
                return None
            try:
                # Optimized for speed instead of strptime
                day = int(d_str[0:2])
                month = int(d_str[2:4])
                year = int(d_str[4:8])
                return datetime(year, month, day)
            except ValueError:
                return None

        def parse_float(v_str):
            if not v_str:
                return None
            try:
                return float(v_str.replace(',', '.'))
            except ValueError:
                return None
            
        return {
            "ind_oper": ind_oper,
            "ind_emit": ind_emit,
            "cod_part": cod_part,
            "modelo": modelo,
            "cod_sit": cod_sit,
            "serie": serie,
            "numero": int(numero) if numero and numero.isdigit() else None,
            "chave_nfe": chave_nfe if chave_nfe else None,
            "data_doc": parse_date(dt_doc_str),
            "data_entrada_saida": parse_date(dt_e_s_str),
            "valor_doc": parse_float(vl_doc_str),
            "linha_original": linha
        }
