"""Ferramentas MCP para consulta de CNPJ."""

from typing import Any

from mcp_fiscal_brasil._core import FiscalValidationError, get_logger

from ..shared.exceptions import ValidationError as SharedValidationError
from ..shared.validators import format_cnpj, normalizar_cnpj, validate_cnpj_qualquer
from .client import CNPJClient
from .schemas import CNPJResponse

logger = get_logger(__name__)
_INVALID_CNPJ_REASON = (
    "CNPJ inválido. Verifique os 14 caracteres (numérico ou alfanumérico) e o dígito verificador."
)


class _CNPJValidationError(FiscalValidationError, SharedValidationError):
    """Validation error compatible with both core and legacy fiscal errors."""

    def __init__(self, field: str, value: str, reason: str) -> None:
        message = f"Valor inválido para '{field}': {value!r}. {reason}"
        detail = {"field": field, "value": value, "reason": reason}
        Exception.__init__(self, message)
        self.message = message
        self.detail = detail
        self.field = field
        self.value = value
        self.code = "VALIDATION_ERROR"
        self.details = {"field": field, "value": value}
        self.reason = reason


_client = CNPJClient()


async def consultar_cnpj(cnpj: str) -> CNPJResponse:
    """
    Consulta os dados cadastrais de uma empresa pelo CNPJ.

    Aceita o CNPJ numérico ou alfanumérico (IN RFB 2.229/2024), com ou sem
    formatação (pontos, barra, traço).
    Retorna razão social, endereço, atividades econômicas, sócios e situação cadastral.

    Args:
        cnpj: Número do CNPJ (ex: '11.222.333/0001-81', '11222333000181'
            ou '12ABC34501DE35')

    Returns:
        CNPJResponse com os dados completos da empresa.

    Raises:
        ValidationError: Se o CNPJ for inválido.
        NotFoundError: Se o CNPJ não for encontrado na Receita Federal.
        APIError: Em caso de falha nas APIs consultadas.
    """
    # Valida o valor bruto (aceita só a máscara padrão; espaços e outros
    # caracteres são rejeitados) e normaliza somente depois de aceito.
    if not validate_cnpj_qualquer(cnpj):
        raise _CNPJValidationError(field="cnpj", value=cnpj, reason=_INVALID_CNPJ_REASON)
    cnpj_normalizado = normalizar_cnpj(cnpj)

    cnpj_formatado = format_cnpj(cnpj_normalizado)
    logger.info("cnpj_lookup_requested", cnpj=cnpj_formatado)
    return await _client.consultar(cnpj_normalizado)


async def listar_cnpjs_por_nome(nome: str, uf: str | None = None) -> dict[str, Any]:
    """
    Busca empresas pelo nome ou razão social (funcionalidade NÃO suportada).

    APIs públicas gratuitas não cobrem busca textual por nome. Em vez de uma lista
    com um item de aviso (que um cliente poderia tratar como resultado), retorna um
    objeto explícito com ``suportado=False`` e ``resultados`` vazio.

    Args:
        nome: Nome ou parte da razão social da empresa.
        uf: Sigla do estado para filtrar (ex: 'SP', 'MG'). Opcional.

    Returns:
        dict com suportado (False), status, resultados (lista vazia), motivo e
        alternativa.
    """
    logger.info("cnpj_name_lookup_limited", nome=nome, uf=uf)
    return {
        "suportado": False,
        "status": "busca_por_nome_indisponivel",
        "nome": nome,
        "uf": uf,
        "resultados": [],
        "motivo": (
            "A busca por nome de empresa requer APIs pagas ou o portal da Receita "
            "Federal; as fontes públicas gratuitas usadas aqui não oferecem esse recurso."
        ),
        "alternativa": "Obtenha o CNPJ por outra fonte e use consultar_cnpj.",
    }
