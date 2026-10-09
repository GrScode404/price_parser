from decimal import Decimal

import redis.asyncio as redis


class RedisStorage:
    def __init__(self, client: redis.Redis):
        self.client = client

    async def save_price(self, product_id: int, price: Decimal) -> None:
        key = f"product:{product_id}"
        await self.client.set(key, str(price))

    async def get_price(self, product_id: int) -> Decimal | None:
        key = f"product:{product_id}"
        value = await self.client.get(key)

        if value is None:
            return None
        
        if isinstance(value, bytes):
            value = value.decode("utf-8")

        return Decimal(value)
