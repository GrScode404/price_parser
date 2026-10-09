from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from price_parser.storage import RedisStorage


@pytest.mark.asyncio
async def test_save_price():
    client = AsyncMock()
    storage = RedisStorage(client)

    price = Decimal("155.62")
    await storage.save_price(1, str(price))

    client.set.assert_awaited_once_with("product:1", "155.62")


@pytest.mark.asyncio
async def test_get_price():
    client = AsyncMock()
    client.get.return_value = "155.62"

    storage = RedisStorage(client)

    result = await storage.get_price(1)

    assert result == Decimal("155.62")
    assert isinstance(result, Decimal)
    client.get.assert_awaited_once_with("product:1")


@pytest.mark.asyncio
async def test_get_price_when_key_does_not_exist():
    client = AsyncMock()
    client.get.return_value = None

    storage = RedisStorage(client)

    result = await storage.get_price(1)

    assert result is None
