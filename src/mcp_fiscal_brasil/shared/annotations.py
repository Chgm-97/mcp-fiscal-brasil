"""Anotacoes MCP (readOnlyHint, destructiveHint, ...) para as ferramentas.

Clientes MCP usam essas dicas para decidir quando pedir confirmacao ao usuario
e quais ferramentas podem ser chamadas em paralelo com seguranca. Em vez de
repetir ``annotations=...`` em cada decorador (45 ferramentas, em varios
modulos), ``instalar_anotacoes`` embrulha ``app.tool`` e injeta o padrao pelo
nome da ferramenta. Quem declarar ``annotations`` explicitamente no decorador
mantem o valor declarado.
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

# Unica ferramenta que altera estado externo: registra um evento fiscal na SEFAZ.
# Ciencia/Confirmacao/Desconhecimento nao podem ser desfeitos livremente.
FERRAMENTAS_COM_EFEITO: frozenset[str] = frozenset({"manifestar_nfe"})

# Ferramentas que rodam so localmente (validacao, parsing, tabelas embarcadas,
# simulacoes) ou que apenas devolvem orientacao: nao acessam servicos externos.
FERRAMENTAS_LOCAIS: frozenset[str] = frozenset(
    {
        "validar_cpf",
        "validar_chave_nfe",
        "parse_nfe_xml",
        "gerar_danfe",
        "validar_assinatura_nfe",
        "analisar_sped",
        "listar_registros_sped",
        "listar_eventos_esocial",
        "validar_evento_esocial",
        "consultar_certidao_federal",
        "consultar_certidao_fgts",
        "compare_tax_regimes",
        "simular_transicao_reforma_tributaria",
        "consultar_ncm",
        "consultar_cfop",
        "validar_cst",
        "consultar_cest",
        "consultar_aliquota_icms",
        "consultar_aliquotas_importacao",
        "calcular_tributos_importacao",
    }
)


def anotacoes_para(nome: str) -> ToolAnnotations:
    """Retorna as anotacoes MCP padrao da ferramenta ``nome``."""
    if nome in FERRAMENTAS_COM_EFEITO:
        return ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=True,
        )
    return ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=nome not in FERRAMENTAS_LOCAIS,
    )


def instalar_anotacoes(app: Any) -> None:
    """Faz ``app.tool(name=...)`` injetar anotacoes quando nao declaradas."""
    original = app.tool

    def tool(*args: Any, **kwargs: Any) -> Any:
        nome = kwargs.get("name")
        if isinstance(nome, str) and "annotations" not in kwargs:
            kwargs["annotations"] = anotacoes_para(nome)
        return original(*args, **kwargs)

    app.tool = tool


__all__ = [
    "FERRAMENTAS_COM_EFEITO",
    "FERRAMENTAS_LOCAIS",
    "anotacoes_para",
    "instalar_anotacoes",
]
