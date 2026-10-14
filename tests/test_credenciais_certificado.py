"""Senha e caminho do certificado A1 podem vir do ambiente, sem passar pelo modelo."""

import pytest

from mcp_fiscal_brasil import server
from mcp_fiscal_brasil.server import _credenciais_certificado, app


def test_usa_ambiente_quando_parametros_omitidos(monkeypatch):
    monkeypatch.setattr(server.settings, "nfe_certificado_path", "/certs/a1.pfx")
    monkeypatch.setattr(server.settings, "nfe_certificado_senha", "segredo")
    assert _credenciais_certificado(None, None) == ("/certs/a1.pfx", "segredo")


def test_parametro_explicito_tem_precedencia(monkeypatch):
    monkeypatch.setattr(server.settings, "nfe_certificado_path", "/certs/a1.pfx")
    monkeypatch.setattr(server.settings, "nfe_certificado_senha", "segredo")
    assert _credenciais_certificado("/outro.pfx", "outra") == ("/outro.pfx", "outra")


def test_erro_claro_sem_configuracao(monkeypatch):
    monkeypatch.setattr(server.settings, "nfe_certificado_path", "")
    monkeypatch.setattr(server.settings, "nfe_certificado_senha", "")
    with pytest.raises(ValueError, match="NFE_CERTIFICADO_SENHA"):
        _credenciais_certificado(None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("nome", ["baixar_nfe_distribuicao", "manifestar_nfe"])
async def test_senha_nao_e_parametro_obrigatorio(nome):
    tools = {t.name: t for t in await app.list_tools()}
    obrigatorios = tools[nome].parameters.get("required", [])
    assert "senha" not in obrigatorios
    assert "caminho_certificado" not in obrigatorios
