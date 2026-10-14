"""CNPJ alfanumerico (IN RFB 2.229/2024) em certidoes e NFS-e."""

import pytest

from mcp_fiscal_brasil.certidoes.client import get_pgfn_url
from mcp_fiscal_brasil.certidoes.tools import (
    consultar_certidao_federal,
    consultar_certidao_fgts,
)
from mcp_fiscal_brasil.nfse.tools import _validar_cnpj_prestador
from mcp_fiscal_brasil.shared.exceptions import ValidationError

CNPJ_ALFA = "12ABC34501DE35"
CNPJ_ALFA_MASCARADO = "12.ABC.345/01DE-35"
CNPJ_ALFA_DV_ERRADO = "12ABC34501DE00"


def test_pgfn_url_cnpj_alfanumerico_usa_pj():
    assert "PJ/Emitir" in get_pgfn_url(CNPJ_ALFA).url
    assert "PJ/Emitir" in get_pgfn_url(CNPJ_ALFA_MASCARADO).url


@pytest.mark.asyncio
@pytest.mark.parametrize("doc", [CNPJ_ALFA, CNPJ_ALFA_MASCARADO])
async def test_certidao_federal_aceita_cnpj_alfanumerico(doc):
    r = await consultar_certidao_federal(doc)
    assert r["tipo_documento"] == "CNPJ"
    assert "PJ/Emitir" in r["url_emissao"]


@pytest.mark.asyncio
async def test_certidao_federal_rejeita_dv_alfanumerico_errado():
    with pytest.raises(ValidationError):
        await consultar_certidao_federal(CNPJ_ALFA_DV_ERRADO)


@pytest.mark.asyncio
async def test_certidao_fgts_aceita_cnpj_alfanumerico():
    r = await consultar_certidao_fgts(CNPJ_ALFA)
    assert r["status"] == "consulta_manual_necessaria"


def test_nfse_prestador_alfanumerico_normalizado():
    assert _validar_cnpj_prestador(CNPJ_ALFA_MASCARADO) == CNPJ_ALFA


def test_nfse_prestador_alfanumerico_invalido():
    with pytest.raises(ValueError):
        _validar_cnpj_prestador(CNPJ_ALFA_DV_ERRADO)
