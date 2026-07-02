import pytest
from app.services.xml_parser import XMLParser
from datetime import datetime

def test_parse_nfe_model_55():
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35230112345678000199550010000001231000001234" versao="4.00">
      <ide>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>123</nNF>
        <dhEmi>2023-01-05T10:00:00-03:00</dhEmi>
      </ide>
      <emit>
        <CNPJ>12345678000199</CNPJ>
        <xNome>EMPRESA TESTE</xNome>
      </emit>
      <dest>
        <CNPJ>99888777000122</CNPJ>
        <xNome>CLIENTE TESTE</xNome>
      </dest>
      <total>
        <ICMSTot>
          <vNF>1500.50</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
  <protNFe versao="4.00">
    <infProt>
      <cStat>100</cStat>
    </infProt>
  </protNFe>
</nfeProc>"""

    res = XMLParser.parse(xml_content)
    
    assert res["chave_nfe"] == "35230112345678000199550010000001231000001234"
    assert res["modelo"] == "55"
    assert res["serie"] == "1"
    assert res["numero"] == 123
    assert res["cnpj_emitente"] == "12345678000199"
    assert res["cnpj_destinatario"] == "99888777000122"
    assert res["valor_total"] == 1500.50
    assert res["situacao"] == "AUTORIZADA"
    assert res["data_emissao"] == datetime(2023, 1, 5, 10, 0, 0)
