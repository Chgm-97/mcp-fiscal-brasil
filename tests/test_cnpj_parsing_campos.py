"""Nomes reais dos campos da BrasilAPI e da ReceitaWS (sem acento).

O parser lia "número", "código" e "descrição", chaves que nenhuma das APIs
devolve: o número do endereço sempre sumia e as atividades secundárias da
BrasilAPI eram descartadas.
"""

from mcp_fiscal_brasil.cnpj.client import CNPJClient

BRASIL_API = {
    "razao_social": "PETROLEO BRASILEIRO S A PETROBRAS",
    "descricao_situacao_cadastral": "ATIVA",
    "cnae_fiscal": 600001,
    "cnae_fiscal_descricao": "Extração de petróleo e gás natural",
    "cnaes_secundarios": [
        {"codigo": 1921700, "descricao": "Fabricação de produtos do refino de petróleo"},
        {"codigo": 0, "descricao": ""},
    ],
    "descricao_tipo_de_logradouro": "AVENIDA",
    "logradouro": "REPUBLICA DO CHILE",
    "numero": "65",
    "municipio": "RIO DE JANEIRO",
    "uf": "RJ",
}

RECEITA_WS = {
    "nome": "APROCON CONTABIL LTDA",
    "situacao": "ATIVA",
    "atividade_principal": [{"code": "69.20-6-01", "text": "Atividades de contabilidade"}],
    "atividades_secundarias": [{"code": "00.00-0-00", "text": "Não informada"}],
    "logradouro": "ALAMEDA DOS GUAIOS",
    "numero": "456",
}


def test_brasil_api_le_secundarias_numero_e_tipo_de_logradouro():
    r = CNPJClient()._parse_brasil_api(BRASIL_API, "33000167000101")
    assert [a.código for a in r.atividades_secundarias] == ["1921700"]
    assert r.endereco is not None
    assert r.endereco.número == "65"
    assert r.endereco.logradouro == "AVENIDA REPUBLICA DO CHILE"


def test_brasil_api_nao_duplica_tipo_ja_presente():
    dados = {**BRASIL_API, "logradouro": "AVENIDA REPUBLICA DO CHILE"}
    r = CNPJClient()._parse_brasil_api(dados, "33000167000101")
    assert r.endereco is not None
    assert r.endereco.logradouro == "AVENIDA REPUBLICA DO CHILE"


def test_receita_ws_le_numero_e_ignora_cnae_nao_informado():
    r = CNPJClient()._parse_receita_ws(RECEITA_WS, "45882222000113")
    assert r.atividades_secundarias == []
    assert r.endereco is not None
    assert r.endereco.número == "456"
