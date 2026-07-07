import io
import csv
from typing import List, Dict, Any
import openpyxl

class ExporterService:
    @staticmethod
    def export_excel(data: List[Dict[str, Any]]) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Conciliacao"

        headers = [
            "Status da conciliação", "Chave da NF-e", "CNPJ emitente", "CNPJ destinatário",
            "Nome do participante", "Modelo", "Série", "Número", "Data de emissão",
            "Data de entrada/saída", "Valor no XML", "Valor no SPED", "Diferença",
            "Situação da nota", "Origem do documento", "Observação do sistema"
        ]
        ws.append(headers)

        for row in data:
            diferenca = row.get("diferenca")
            if isinstance(diferenca, dict) or isinstance(diferenca, list):
                import json
                diferenca = json.dumps(diferenca, ensure_ascii=False)
                
            ws.append([
                row.get("status"), row.get("chave_nfe"), row.get("cnpj_emitente"), row.get("cnpj_destinatario"),
                row.get("nome_participante"), row.get("modelo"), row.get("serie"), row.get("numero"),
                row.get("data_emissao"), row.get("data_entrada_saida"), row.get("valor_xml"),
                row.get("valor_sped"), diferenca, row.get("situacao_nota"),
                row.get("origem_documento"), row.get("observacao")
            ])
            
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    @staticmethod
    def export_csv(data: List[Dict[str, Any]]) -> str:
        output = io.StringIO()
        headers = [
            "Status da conciliação", "Chave da NF-e", "CNPJ emitente", "CNPJ destinatário",
            "Nome do participante", "Modelo", "Série", "Número", "Data de emissão",
            "Data de entrada/saída", "Valor no XML", "Valor no SPED", "Diferença",
            "Situação da nota", "Origem do documento", "Observação do sistema"
        ]
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        for row in data:
            diferenca = row.get("diferenca")
            if isinstance(diferenca, dict) or isinstance(diferenca, list):
                import json
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
            
        return output.getvalue()
