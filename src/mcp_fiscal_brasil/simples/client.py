from datetime import date
from typing import Any

from mcp_fiscal_brasil._core import (
    FiscalNotFoundError,
    HTTPClient,
    get_logger,
    settings,
)
from mcp_fiscal_brasil._core.errors import FiscalHTTPError

from ..shared.validators import normalizar_cnpj, validate_cnpj_qualquer
from .schemas import SimplesStatus

logger = get_logger(__name__)


def _primeiro(*valores: Any) -> Any:
    """Primeiro valor que nao seja None (False e um valor valido)."""
    return next((v for v in valores if v is not None), None)


def extrair_regime(data: dict[str, Any]) -> dict[str, Any]:
    """Extrai opcao pelo Simples Nacional e MEI de uma resposta da BrasilAPI.

    A fonte e o ``/cnpj/v1/{cnpj}`` (campos ``opcao_pelo_simples``,
    ``data_opcao_pelo_simples`` etc). O endpoint ``/simples/v1`` usado
    anteriormente nao existe na BrasilAPI (responde 404 em HTML para qualquer
    CNPJ), o que fazia toda empresa aparecer como nao optante. Os formatos
    antigos (``simples``/``simei`` aninhados ou chaves na raiz) seguem aceitos.

    ``fonte_confirmada`` e False quando a resposta nao traz a opcao pelo Simples.
    """
    simples_bruto = data.get("simples")
    simei_bruto = data.get("simei")
    simples: dict[str, Any] = simples_bruto if isinstance(simples_bruto, dict) else {}
    simei: dict[str, Any] = simei_bruto if isinstance(simei_bruto, dict) else {}
    optante_simples = _primeiro(
        data.get("opcao_pelo_simples"), simples.get("optante"), data.get("simples_nacional")
    )
    optante_mei = _primeiro(data.get("opcao_pelo_mei"), simei.get("optante"), data.get("mei"))
    return {
        "simples_nacional": bool(optante_simples),
        "data_opcao": _primeiro(
            data.get("data_opcao_pelo_simples"),
            simples.get("data_opcao"),
            data.get("data_opcao_simples"),
        ),
        "data_exclusao": _primeiro(
            data.get("data_exclusao_do_simples"),
            simples.get("data_exclusao"),
            data.get("data_exclusao_simples"),
        ),
        "mei": bool(optante_mei),
        "data_opcao_mei": _primeiro(
            data.get("data_opcao_pelo_mei"), simei.get("data_opcao"), data.get("data_opcao_simei")
        ),
        "data_exclusao_mei": _primeiro(
            data.get("data_exclusao_do_mei"),
            simei.get("data_exclusao"),
            data.get("data_exclusao_simei"),
        ),
        "fonte_confirmada": optante_simples is not None,
    }


class SimplesClient:
    """Cliente para consulta do Simples Nacional via BrasilAPI."""

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

    async def get_simples_status(self, cnpj: str) -> SimplesStatus:
        """Consulta o status do Simples Nacional e MEI para um CNPJ."""
        cnpj_clean = normalizar_cnpj(cnpj)
        if not validate_cnpj_qualquer(cnpj_clean):
            # CNPJ com digito verificador invalido nunca existe: rejeita localmente,
            # sem bater na API.
            raise FiscalNotFoundError("CNPJ inválido", "CNPJ", cnpj_clean)

        logger.info("simples_status_started", cnpj=cnpj_clean)
        async with self._http_client() as client:
            try:
                data = await client.get(f"/cnpj/v1/{cnpj_clean}")
            except FiscalHTTPError as exc:
                if exc.status_code == 404:
                    # CNPJ sem dados na BrasilAPI: a fonte nao confirma o regime.
                    logger.warning("simples_status_nao_confirmado", cnpj=cnpj_clean)
                    return SimplesStatus(
                        cnpj=cnpj_clean,
                        simples_nacional=False,
                        mei=False,
                        fonte_confirmada=False,
                    )
                raise

        regime = extrair_regime(data)
        return SimplesStatus(
            cnpj=cnpj_clean,
            simples_nacional=regime["simples_nacional"],
            data_opcao=self._parse_date(regime["data_opcao"]),
            data_exclusao=self._parse_date(regime["data_exclusao"]),
            mei=regime["mei"],
            data_opcao_mei=self._parse_date(regime["data_opcao_mei"]),
            data_exclusao_mei=self._parse_date(regime["data_exclusao_mei"]),
            fonte_confirmada=regime["fonte_confirmada"],
        )
