import logging
import httpx
from app.core.config import settings
from datetime import datetime
import json
import base64

logger = logging.getLogger(__name__)

class SiegConnector:
    def __init__(self, api_key: str = None, email: str = None):
        self.api_key = api_key or settings.SIEG_API_KEY
        self.email = email or settings.SIEG_EMAIL
        self.base_url = f"https://api.sieg.com/BaixarXmls?api_key={self.api_key}"

    def sync_documents(self, empresa_cnpj: str, periodo: str) -> dict:
        """
        Integração com a API SIEG V1 (Legado)
        """
        if not self.api_key:
            logger.warning("SIEG integration not configured. Missing API key.")
            return {
                "status": "pending_configuration",
                "message": "Integração SIEG não configurada. Defina SIEG_API_KEY no ambiente.",
                "downloaded_count": 0
            }
        
        # Periodo is YYYY-MM
        try:
            dt = datetime.strptime(periodo, "%Y-%m")
            import calendar
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            data_inicio = f"{dt.year}-{dt.month:02d}-01T00:00:00"
            data_fim = f"{dt.year}-{dt.month:02d}-{last_day}T23:59:59"
        except ValueError:
            data_inicio = f"{periodo}T00:00:00"
            data_fim = f"{periodo}T23:59:59"

        xmls_base64 = []
        errors = []

        try:
            with httpx.Client(timeout=120.0) as client:
                for cnpj_key in ["CnpjDest", "CnpjEmit"]:
                    payload = {
                        "Email": self.email,
                        cnpj_key: empresa_cnpj,
                        "DataEmissaoInicio": data_inicio,
                        "DataEmissaoFim": data_fim,
                        "TipoXml": 1
                    }
                    
                    response = client.post(
                        self.base_url, 
                        json=payload
                    )
                    
                    if response.status_code == 404 and "Nenhum arquivo XML localizado" in response.text:
                        continue
                    
                    if response.status_code == 400:
                        logger.error(f"SIEG 400 Bad Request: {response.text}")
                        errors.append(f"Erro na API SIEG (400): {response.text}")
                        continue
                    
                    if response.status_code == 401:
                        logger.error(f"SIEG 401 Unauthorized: {response.text}")
                        errors.append("Acesso Negado (401) na API SIEG.")
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # A API retorna um objeto que contém 'Xmls' (lista de strings em Base64) em caso de sucesso
                    xmls_base64.extend(data.get("Xmls", []))
                
                if not xmls_base64 and not errors:
                    return {
                        "status": "success",
                        "message": "Nenhum documento encontrado para o período informado.",
                        "downloaded_count": 0
                    }
                
                if errors and not xmls_base64:
                    return {
                        "status": "error",
                        "message": " | ".join(errors),
                        "downloaded_count": 0
                    }
                
                return {
                    "status": "success",
                    "message": "Sincronização concluída",
                    "downloaded_count": len(xmls_base64),
                    "xmls": xmls_base64
                }
                
        except Exception as e:
            logger.error(f"Erro ao chamar API SIEG: {e}")
            return {
                "status": "error",
                "message": f"Erro de comunicação com a API SIEG: {str(e)}",
                "downloaded_count": 0
            }
