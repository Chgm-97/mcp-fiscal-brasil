from unittest.mock import patch

import pytest

from mcp_fiscal_brasil._core.errors import FiscalHTTPError, FiscalNotFoundError
from mcp_fiscal_brasil.mei.client import MEIClient


@pytest.fixture
def client():
    return MEIClient()


@pytest.mark.asyncio
async def test_get_mei_status_success(client):
    with patch("mcp_fiscal_brasil._core.http.HTTPClient.get") as mock_get:
        mock_get.return_value = {"simples": {"optante": True}, "simei": {"optante": True}}
        result = await client.get_mei_status("123")
        assert result.mei is True
        assert result.simples_nacional is True


@pytest.mark.asyncio
async def test_get_mei_status_fallback_format(client):
    with patch("mcp_fiscal_brasil._core.http.HTTPClient.get") as mock_get:
        mock_get.return_value = {"mei": False, "simples_nacional": False}
        result = await client.get_mei_status("123")
        assert result.mei is False
        assert result.simples_nacional is False


@pytest.mark.asyncio
async def test_get_mei_status_not_found(client):
    with patch("mcp_fiscal_brasil._core.http.HTTPClient.get") as mock_get:
        mock_get.side_effect = FiscalHTTPError("Not found", 404, "http://test")
        with pytest.raises(FiscalNotFoundError):
            await client.get_mei_status("123")


@pytest.mark.asyncio
async def test_get_mei_status_le_campos_do_cnpj_v1():
    from mcp_fiscal_brasil.mei.client import MEIClient

    with patch("mcp_fiscal_brasil._core.http.HTTPClient.get") as mock_get:
        mock_get.return_value = {
            "opcao_pelo_simples": True,
            "opcao_pelo_mei": True,
            "data_opcao_pelo_mei": "2022-03-01",
        }
        result = await MEIClient().get_mei_status("45882222000113")
        mock_get.assert_called_once_with("/cnpj/v1/45882222000113")
        assert result.mei is True
        assert result.simples_nacional is True
        assert result.data_opcao_mei is not None
