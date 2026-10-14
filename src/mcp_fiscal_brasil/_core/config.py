"""Application configuration for mcp-fiscal-brasil."""

import ipaddress
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    mcp_fiscal_env: str = "development"
    mcp_fiscal_log_level: str = "INFO"
    mcp_fiscal_cache_ttl: int = 300
    mcp_fiscal_rate_limit: int = 10
    mcp_fiscal_http_timeout: float = 30.0
    mcp_fiscal_max_retries: int = 3
    mcp_fiscal_file_base_dir: str = "~/.local/share/mcp-fiscal-brasil/files"

    # Modo remoto do servidor MCP (transportes http/sse/streamable-http). Ativado
    # automaticamente por main() quando o transporte nao e stdio; esta variavel
    # forca o modo para quem sobe o app por outro caminho (ex: uvicorn/fastmcp run).
    # Em modo remoto: caminhos de arquivo ficam confinados a MCP_FISCAL_FILE_BASE_DIR
    # e as ferramentas que usam certificado A1 ficam bloqueadas por padrao.
    mcp_fiscal_modo_remoto: bool = False
    # Token Bearer exigido nos transportes HTTP do servidor MCP. Vazio = sem
    # autenticacao (apenas para uso em rede confiavel).
    mcp_fiscal_auth_token: str = ""
    # Libera baixar_nfe_distribuicao/manifestar_nfe em modo remoto. So tem efeito
    # com MCP_FISCAL_AUTH_TOKEN definido.
    mcp_fiscal_permitir_certificado_remoto: bool = False
    # Restringe a execucao a esta maquina: so stdio ou HTTP/SSE em loopback
    # (127.0.0.1, ::1, localhost). Qualquer bind em interface de rede e recusado.
    mcp_fiscal_somente_local: bool = False
    brasilapi_base_url: str = "https://brasilapi.com.br/api"
    receita_base_url: str = "https://receitaws.com.br/v1"

    # Provedor premium opcional cpfcnpj.com.br (opt-in). Sem token configurado, o
    # servico opera exatamente como antes, usando apenas as fontes gratuitas. Ao
    # definir CPFCNPJ_TOKEN, as consultas de CNPJ (pacotes 5/6) e de NF-e/NFC-e por
    # chave (pacotes 100/102) passam a tentar primeiro a cpfcnpj.com.br, com dados
    # oficiais em tempo real, e mantem as fontes gratuitas como fallback.
    cpfcnpj_token: str = ""
    cpfcnpj_base_url: str = "https://api.cpfcnpj.com.br"
    cpfcnpj_cnpj_packet: int = 6
    ibge_cnae_base_url: str = "https://servicodados.ibge.gov.br/api/v2/cnae"
    ibge_localidades_base_url: str = "https://servicodados.ibge.gov.br/api/v1/localidades"
    bcb_sgs_base_url: str = "https://api.bcb.gov.br/dados/serie"

    # Certificado digital A1 (e-CNPJ) para consultas mTLS aos webservices SEFAZ
    # (status de servico, distribuicao, manifestacao). Configurado via secret/volume
    # montado no deploy (Cloud Run --set-secrets, Fly.io secrets ou volume Docker),
    # nunca em texto plano no .env de producao.
    nfe_certificado_path: str = ""
    nfe_certificado_senha: str = ""
    nfe_emitente_cnpj: str = ""
    nfe_ambiente: str = "producao"

    # ".env" e relativo ao diretorio de trabalho, que para clientes MCP (Claude
    # Desktop/Code) costuma ser outro. MCP_FISCAL_ENV_FILE aponta um caminho
    # absoluto; quando definido, tem precedencia sobre o .env do diretorio atual.
    model_config = SettingsConfigDict(
        env_file=tuple(f for f in (".env", os.environ.get("MCP_FISCAL_ENV_FILE")) if f),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cpfcnpj_base_url")
    @classmethod
    def _exigir_https_cpfcnpj(cls, valor: str) -> str:
        """Exige HTTPS na base da cpfcnpj.com.br.

        O token da conta viaja no caminho da URL (``/{token}/{pacote}/{documento}``),
        portanto a base nao pode usar ``http://``, mesmo quando sobrescrita por
        variavel de ambiente, sob pena de expor o token sem criptografia.
        """
        normalizado = valor.strip()
        if not normalizado.lower().startswith("https://"):
            raise ValueError(
                "CPFCNPJ_BASE_URL deve usar https:// (o token da conta viaja no "
                "caminho da URL e nao pode trafegar sem criptografia)."
            )
        return normalizado


def host_e_local(host: str) -> bool:
    """True quando o host so aceita conexoes desta maquina (loopback)."""
    if host.strip().lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip().strip("[]")).is_loopback
    except ValueError:
        return False


def exigir_execucao_local(transporte: str, host: str) -> None:
    """Com MCP_FISCAL_SOMENTE_LOCAL, recusa expor o servidor fora do loopback."""
    if not settings.mcp_fiscal_somente_local or transporte == "stdio":
        return
    if not host_e_local(host):
        raise SystemExit(
            f"MCP_FISCAL_SOMENTE_LOCAL ativo: recusando escutar em '{host}'. "
            "Use o transporte stdio ou HOST=127.0.0.1."
        )


settings = Settings()

__all__ = ["Settings", "exigir_execucao_local", "host_e_local", "settings"]
