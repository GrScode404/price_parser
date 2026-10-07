import redis.asyncio as redis


class RedisStorage:
    def __init__(self, client: redis.Redis):
        self.client = client

    async def save_price(self, product_id: int, price: float) -> None:
        key = f"product:{product_id}"
        await self.client.set(key, price)

    async def get_price(self, product_id: int) -> float | None:
        key = f"product:{product_id}"
        value = await self.client.get(key)

        if value is None:
            return None

        return float(value)