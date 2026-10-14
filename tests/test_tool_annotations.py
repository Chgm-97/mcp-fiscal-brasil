"""Todas as ferramentas MCP devem expor anotacoes de seguranca."""

import pytest

from mcp_fiscal_brasil.server import app
from mcp_fiscal_brasil.shared.annotations import (
    FERRAMENTAS_COM_EFEITO,
    FERRAMENTAS_LOCAIS,
)


def _dicas(tool) -> dict:
    """Anotacoes com os nomes do protocolo (camelCase), estaveis entre versoes do SDK."""
    return tool.annotations.model_dump(by_alias=True, exclude_none=True)


@pytest.fixture(scope="module")
async def tools():
    return {t.name: t for t in await app.list_tools()}


@pytest.mark.asyncio
async def test_toda_ferramenta_tem_anotacoes(tools):
    sem = [n for n, t in tools.items() if t.annotations is None]
    assert not sem, f"sem anotacoes: {sem}"


@pytest.mark.asyncio
async def test_manifestar_nfe_e_destrutiva(tools):
    a = _dicas(tools["manifestar_nfe"])
    assert a["readOnlyHint"] is False
    assert a["destructiveHint"] is True
    assert a["idempotentHint"] is False


@pytest.mark.asyncio
async def test_demais_ferramentas_sao_somente_leitura(tools):
    for nome, t in tools.items():
        if nome in FERRAMENTAS_COM_EFEITO:
            continue
        a = _dicas(t)
        assert a["readOnlyHint"] is True, nome
        assert a["destructiveHint"] is False, nome


@pytest.mark.asyncio
async def test_ferramentas_locais_nao_sao_open_world(tools):
    for nome in FERRAMENTAS_LOCAIS:
        assert nome in tools, f"{nome} nao existe mais; atualize FERRAMENTAS_LOCAIS"
        assert _dicas(tools[nome])["openWorldHint"] is False, nome
    assert _dicas(tools["consultar_cnpj"])["openWorldHint"] is True
