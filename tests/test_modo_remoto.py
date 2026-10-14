"""Protecoes do servidor MCP em modo remoto (http/sse): caminhos, certificado e auth."""

import httpx
import pytest

from mcp_fiscal_brasil import server


@pytest.fixture
def remoto(monkeypatch, tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(server, "_transporte_remoto", True)
    monkeypatch.setattr(server.settings, "mcp_fiscal_file_base_dir", str(base))
    monkeypatch.setattr(server.settings, "mcp_fiscal_auth_token", "")
    monkeypatch.setattr(server.settings, "mcp_fiscal_permitir_certificado_remoto", False)
    monkeypatch.setattr(server.settings, "nfe_certificado_path", "/certs/a1.pfx")
    monkeypatch.setattr(server.settings, "nfe_certificado_senha", "segredo")
    return base


# --- caminhos de arquivo ---------------------------------------------------


def test_stdio_nao_restringe_caminho(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "_transporte_remoto", False)
    monkeypatch.setattr(server.settings, "mcp_fiscal_modo_remoto", False)
    fora = str(tmp_path / "qualquer.xml")
    assert server._caminho_entrada(fora, label="X") == fora


def test_remoto_aceita_arquivo_dentro_da_base(remoto):
    arquivo = remoto / "nota.xml"
    arquivo.write_text("<x/>")
    assert server._caminho_entrada(str(arquivo), label="X") == str(arquivo.resolve())


def test_remoto_resolve_relativo_a_partir_da_base(remoto):
    (remoto / "sped.txt").write_text("|0000|")
    assert server._caminho_entrada("sped.txt", label="X") == str((remoto / "sped.txt").resolve())


def test_remoto_bloqueia_arquivo_fora_da_base(remoto, tmp_path):
    fora = tmp_path / "segredo.txt"
    fora.write_text("x")
    with pytest.raises(PermissionError, match="fora do diretorio permitido"):
        server._caminho_entrada(str(fora), label="Arquivo XML")


def test_remoto_bloqueia_traversal_relativo(remoto):
    with pytest.raises(PermissionError):
        server._caminho_entrada("../segredo.txt", label="X")


def test_modo_remoto_forcado_por_configuracao(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "_transporte_remoto", False)
    monkeypatch.setattr(server.settings, "mcp_fiscal_modo_remoto", True)
    monkeypatch.setattr(server.settings, "mcp_fiscal_file_base_dir", str(tmp_path / "base"))
    with pytest.raises(PermissionError):
        server._caminho_entrada(str(tmp_path / "fora.xml"), label="X")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "arg"),
    [("tool_validate_nfe_full", "xml_path"), ("tool_summarize_sped", "file_path")],
)
async def test_tools_de_arquivo_bloqueiam_fora_da_base(remoto, tmp_path, tool, arg):
    fora = tmp_path / "fora.txt"
    fora.write_text("x")
    with pytest.raises(PermissionError):
        await getattr(server, tool)(**{arg: str(fora)})


# --- certificado A1 --------------------------------------------------------


def test_remoto_bloqueia_certificado_por_padrao(remoto):
    with pytest.raises(PermissionError, match="MCP_FISCAL_AUTH_TOKEN"):
        server._credenciais_certificado(None, None)


def test_remoto_opt_in_sem_token_continua_bloqueado(remoto, monkeypatch):
    monkeypatch.setattr(server.settings, "mcp_fiscal_permitir_certificado_remoto", True)
    with pytest.raises(PermissionError):
        server._credenciais_certificado(None, None)


def test_remoto_opt_in_com_token_libera(remoto, monkeypatch):
    monkeypatch.setattr(server.settings, "mcp_fiscal_permitir_certificado_remoto", True)
    monkeypatch.setattr(server.settings, "mcp_fiscal_auth_token", "t" * 32)
    assert server._credenciais_certificado(None, None) == ("/certs/a1.pfx", "segredo")


def test_remoto_caminho_certificado_explicito_confinado(remoto, monkeypatch, tmp_path):
    monkeypatch.setattr(server.settings, "mcp_fiscal_permitir_certificado_remoto", True)
    monkeypatch.setattr(server.settings, "mcp_fiscal_auth_token", "t" * 32)
    with pytest.raises(PermissionError):
        server._credenciais_certificado(str(tmp_path / "outro.pfx"), "x")


@pytest.mark.asyncio
async def test_manifestar_nfe_bloqueada_em_modo_remoto(remoto):
    with pytest.raises(PermissionError):
        await server.tool_manifestar_nfe(
            chave="3" * 44, tipo_evento="210220", cnpj_cpf="33000167000101"
        )


# --- autenticacao Bearer ---------------------------------------------------


@pytest.fixture
def auth_restaurado(monkeypatch):
    monkeypatch.setattr(server.app, "auth", None)
    monkeypatch.setattr(server, "_transporte_remoto", False)


async def _post_initialize(headers: dict[str, str]) -> int:
    http_app = server.app.http_app(transport="streamable-http")
    corpo = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "teste", "version": "0"},
        },
    }
    async with http_app.router.lifespan_context(http_app):
        transporte = httpx.ASGITransport(app=http_app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://t") as cliente:
            resposta = await cliente.post(
                "/mcp",
                json=corpo,
                headers={"Accept": "application/json, text/event-stream", **headers},
            )
    return resposta.status_code


@pytest.mark.asyncio
async def test_token_exigido_quando_configurado(auth_restaurado, monkeypatch):
    monkeypatch.setattr(server.settings, "mcp_fiscal_auth_token", "token-correto-123")
    server._configurar_modo_remoto()

    assert await _post_initialize({}) == 401
    assert await _post_initialize({"Authorization": "Bearer errado"}) == 401
    assert await _post_initialize({"Authorization": "Bearer token-correto-123"}) == 200


def test_sem_token_nao_instala_auth(auth_restaurado, monkeypatch):
    monkeypatch.setattr(server.settings, "mcp_fiscal_auth_token", "")
    server._configurar_modo_remoto()
    assert server.app.auth is None
    assert server._modo_remoto()
