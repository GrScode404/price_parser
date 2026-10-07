
import asyncio
import json

import aiohttp
import redis.asyncio as redis
from lxml import html

from price_parser.storage import RedisStorage


MAX_ATTEMPTS = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def load_urls(filename: str) -> list[str]:
    with open(filename, "r") as file:
        return [line.strip() for line in file if line.strip()]


async def fetch(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
) -> str:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        retry_delay = 2 ** (attempt - 1)

        try:
            async with semaphore:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()

                    if (
                        response.status in RETRYABLE_STATUS
                        and attempt < MAX_ATTEMPTS
                    ):
                        retry_after = response.headers.get("Retry-After")

                        if retry_after:
                            try:
                                retry_delay = float(retry_after)
                            except ValueError:
                                pass
                    else:
                        response.raise_for_status()

        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            if (
                isinstance(exc, aiohttp.ClientResponseError)
                and exc.status not in RETRYABLE_STATUS
            ):
                raise

            if attempt == MAX_ATTEMPTS:
                raise

        if attempt < MAX_ATTEMPTS:
            print(
                f"Повтор {attempt + 1}/{MAX_ATTEMPTS}: "
                f"{url}. Ждём {retry_delay} сек."
            )
            await asyncio.sleep(retry_delay)

    raise RuntimeError(f"Не удалось получить страницу: {url}")


def parse_price(content: str) -> float:
    tree = html.fromstring(content)
    json_text = tree.xpath("string(//pre)")

    if not json_text.strip():
        raise ValueError("На странице не найден JSON с данными товара")

    data = json.loads(json_text)
    price = data.get("price")

    if isinstance(price, bool) or not isinstance(price, (int, float)):
        raise ValueError("Цена отсутствует или имеет неверный формат")

    if price < 0:
        raise ValueError(f"Цена не может быть отрицательной: {price}")

    return float(price)


async def process_product(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
    storage: RedisStorage,
) -> bool:
    try:
        content = await fetch(session, url, semaphore)
        price = parse_price(content)

        product_id = url.rstrip("/").split("/")[-1]
        await storage.save_price(int(product_id), price)

    except Exception as exc:
        print(f"ОШИБКА: {url} — {type(exc).__name__}: {exc}")
        return False

    print(f"URL: {url}, Price: {price}")
    return True


async def main() -> None:
    urls = load_urls("products.txt")
    semaphore = asyncio.Semaphore(10)
    timeout = aiohttp.ClientTimeout(total=15)

    redis_client = redis.Redis(
        host="localhost",
        port=6379,
        db=0,
        decode_responses=True,
    )
    storage = RedisStorage(redis_client)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            results = await asyncio.gather(
                *[
                    process_product(
                        session,
                        url, 
                        semaphore,
                        storage
                    )
                    for url in urls
                ]
            )
    finally:
        await redis_client.aclose()

    successful = sum(results)
    failed = len(results) - successful

    print("\nИтоги запуска:")
    print(f"Всего товаров: {len(urls)}")
    print(f"Успешно обработано: {successful}")
    print(f"Ошибок: {failed}")


if __name__ == "__main__":
    asyncio.run(main())