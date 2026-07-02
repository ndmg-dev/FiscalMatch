import pytest
import httpx
from app.services.sieg_connector import SiegConnector
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente reais do .env
load_dotenv(dotenv_path=".env")

def test_sieg_api_endpoint_response():
    """
    Este teste bate no endpoint real da API do SIEG configurada no .env.
    O objetivo é ver o que a API retorna mesmo se o CNPJ for inválido, 
    para validar a conectividade e a estrutura.
    """
    api_key = os.getenv("SIEG_API_KEY")
    if not api_key:
        pytest.skip("SIEG_API_KEY não configurada no .env")
        
    connector = SiegConnector(api_key=api_key, email="seu_email@empresa.com")
    
    # Executa a chamada usando um CNPJ genérico e um período de testes
    result = connector.sync_documents(empresa_cnpj="00000000000000", periodo="2023-01")
    
    # Vamos printar o resultado para que o usuário veja no console (usando pytest -s)
    print("\n[RESULTADO DA API SIEG]:", result)
    
    # Validamos que o connector não quebrou e tratou a resposta (mesmo sendo um 400 Bad Request)
    assert result["status"] in ["success", "error"]
    
    # Se a API retornou error 400 por causa do CNPJ/Email falso, a mensagem deve refletir isso
    if result["status"] == "error":
        assert "Bad request" in result["message"] or "Erro" in result["message"]

