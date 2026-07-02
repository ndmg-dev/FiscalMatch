import pytest
from app.services.sped_parser import SpedParser
from datetime import datetime

def test_parse_sped_0000():
    content = "|0000|010|0|01012023|31012023|EMPRESA TESTE|12345678000199|||35|123|3500000|||A|1|\n"
    parser = SpedParser()
    res = parser.parse(content)
    
    assert res["periodo"] == "2023-01"
    assert res["empresa_cnpj"] == "12345678000199"

def test_parse_sped_0150_and_c100():
    content = """|0000|010|0|01012023|31012023|EMPRESA TESTE|12345678000199|||35|123|3500000|||A|1|
|0150|CLI_01|CLIENTE TESTE 01|1058|99888777000122||123||35|||3550308||
|C100|1|0|CLI_01|55|00|1|123|35230112345678000199550010000001231000001234|05012023|05012023|1500,50|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|"""
    
    parser = SpedParser()
    res = parser.parse(content)
    
    assert len(res["documents"]) == 1
    doc = res["documents"][0]
    
    assert doc["ind_oper"] == "1"
    assert doc["ind_emit"] == "0"
    assert doc["cod_part"] == "CLI_01"
    assert doc["modelo"] == "55"
    assert doc["serie"] == "1"
    assert doc["numero"] == 123
    assert doc["chave_nfe"] == "35230112345678000199550010000001231000001234"
    assert doc["valor_doc"] == 1500.50
    assert doc["data_doc"] == datetime(2023, 1, 5)
    
    # Check participant resolution
    assert doc["nome_part"] == "CLIENTE TESTE 01"
    assert doc["cnpj_part"] == "99888777000122"
