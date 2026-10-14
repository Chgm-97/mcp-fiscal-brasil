"""Ferramentas que apenas orientam devem dizer explicitamente que nao consultaram."""

import pytest

from mcp_fiscal_brasil.certidoes.tools import (
    consultar_certidao_federal,
    consultar_certidao_fgts,
)
from mcp_fiscal_brasil.cnpj.tools import listar_cnpjs_por_nome


@pytest.mark.asyncio
async def test_listar_cnpjs_por_nome_nao_finge_resultado():
    r = await listar_cnpjs_por_nome("Banco do Brasil", "DF")
    assert r["suportado"] is False
    assert r["resultados"] == []
    assert r["alternativa"].startswith("Obtenha o CNPJ")


@pytest.mark.asyncio
async def test_certidoes_marcam_suportado_false():
    federal = await consultar_certidao_federal("00000000000191")
    fgts = await consultar_certidao_fgts("00000000000191")
    assert federal["suportado"] is False
    assert fgts["suportado"] is False
    assert federal["status"] == fgts["status"] == "consulta_manual_necessaria"
