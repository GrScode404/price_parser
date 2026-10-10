import os
from decimal import Decimal

import pytest
import redis.asyncio as redis

from price_parser.storage import RedisStorage


@pytest.mark.asyncio
async def test_save_and_get_price_from_redis():
    async with redis.Redis(
        host=os.getenv("TEST_REDIS_HOST", "127.0.0.1"),
        port=int(os.getenv("TEST_REDIS_PORT", "6380")),
        db=15,
        decode_responses=True,
    ) as client:
        storage = RedisStorage(client)
        product_id = 987654321
        expected_price = Decimal("155.62")

        await storage.save_price(product_id, expected_price)
        actual_price = await storage.get_price(product_id)

        assert actual_price == expected_price
