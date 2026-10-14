"""MCP_FISCAL_SOMENTE_LOCAL e carregamento do .env por caminho absoluto."""

import os
import subprocess
import sys

import pytest

from mcp_fiscal_brasil._core import config


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1", "[::1]", "localhost"])
def test_hosts_de_loopback_sao_locais(host):
    assert config.host_e_local(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.0.10", "exemplo.com.br", ""])
def test_hosts_de_rede_nao_sao_locais(host):
    assert not config.host_e_local(host)


def test_somente_local_recusa_bind_em_rede(monkeypatch):
    monkeypatch.setattr(config.settings, "mcp_fiscal_somente_local", True)
    with pytest.raises(SystemExit, match="MCP_FISCAL_SOMENTE_LOCAL"):
        config.exigir_execucao_local("http", "0.0.0.0")


def test_somente_local_aceita_stdio_e_loopback(monkeypatch):
    monkeypatch.setattr(config.settings, "mcp_fiscal_somente_local", True)
    config.exigir_execucao_local("stdio", "0.0.0.0")
    config.exigir_execucao_local("http", "127.0.0.1")


def test_sem_somente_local_nao_restringe(monkeypatch):
    monkeypatch.setattr(config.settings, "mcp_fiscal_somente_local", False)
    config.exigir_execucao_local("http", "0.0.0.0")


def test_server_main_recusa_http_em_rede(monkeypatch):
    from mcp_fiscal_brasil import server

    monkeypatch.setattr(config.settings, "mcp_fiscal_somente_local", True)
    monkeypatch.setattr(
        sys, "argv", ["mcp-fiscal-brasil", "--transport", "http", "--host", "0.0.0.0"]
    )
    chamado = []
    monkeypatch.setattr(server.app, "run", lambda **kw: chamado.append(kw))
    with pytest.raises(SystemExit):
        server.main()
    assert chamado == []


def test_env_file_absoluto_e_lido_fora_do_diretorio(tmp_path):
    """MCP_FISCAL_ENV_FILE carrega o .env mesmo com outro diretorio de trabalho,
    como acontece quando o Claude inicia o servidor MCP."""
    env_file = tmp_path / "segredos.env"
    env_file.write_text(
        "NFE_AMBIENTE=homologacao\nMCP_FISCAL_SOMENTE_LOCAL=true\nFASTMCP_TRANSPORT=stdio\n",
        encoding="utf-8",
    )
    outro_dir = tmp_path / "cwd"
    outro_dir.mkdir()
    ambiente = {**os.environ, "MCP_FISCAL_ENV_FILE": str(env_file)}
    ambiente.pop("NFE_AMBIENTE", None)
    ambiente.pop("MCP_FISCAL_SOMENTE_LOCAL", None)
    saida = subprocess.run(
        [
            sys.executable,
            "-c",
            "from mcp_fiscal_brasil._core.config import settings as s;"
            "print(s.nfe_ambiente, s.mcp_fiscal_somente_local)",
        ],
        cwd=outro_dir,
        env=ambiente,
        capture_output=True,
        text=True,
        check=True,
    )
    assert saida.stdout.split() == ["homologacao", "True"]
