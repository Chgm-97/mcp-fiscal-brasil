from datetime import date

from mcp_fiscal_brasil._core import FiscalNotFoundError, HTTPClient, get_logger, settings
from mcp_fiscal_brasil._core.errors import FiscalHTTPError
from mcp_fiscal_brasil.shared.validators import normalizar_cnpj
from mcp_fiscal_brasil.simples.client import extrair_regime

from .schemas import MEIStatus

logger = get_logger(__name__)


class MEIClient:
    """Cliente para consulta do MEI via BrasilAPI."""

    def _http_client(self) -> HTTPClient:
        return HTTPClient(
            settings.brasilapi_base_url,
            timeout=settings.mcp_fiscal_http_timeout,
            max_retries=settings.mcp_fiscal_max_retries,
            cache_ttl=settings.mcp_fiscal_cache_ttl,
            rate_limit_per_second=settings.mcp_fiscal_rate_limit,
        )

    def _parse_date(self, date_str: str | None) -> date | None:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except ValueError:
            return None

    async def get_mei_status(self, cnpj: str) -> MEIStatus:
        """Consulta o status MEI de um CNPJ."""
        logger.info("mei_status_started", cnpj=cnpj)
        cnpj_clean = normalizar_cnpj(cnpj)
        async with self._http_client() as client:
            try:
                data = await client.get(f"/cnpj/v1/{cnpj_clean}")
                regime = extrair_regime(data)
                return MEIStatus(
                    cnpj=cnpj_clean,
                    mei=regime["mei"],
                    data_opcao_mei=self._parse_date(regime["data_opcao_mei"]),
                    data_exclusao_mei=self._parse_date(regime["data_exclusao_mei"]),
                    simples_nacional=regime["simples_nacional"],
                )
            except FiscalHTTPError as exc:
                if exc.status_code == 404:
                    raise FiscalNotFoundError("CNPJ não encontrado", "CNPJ", cnpj_clean) from exc
                raise
