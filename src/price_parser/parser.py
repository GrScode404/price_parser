import asyncio

import aiohttp

from lxml import html

import json

def load_urls(filename: str) -> list[str]:
    with open(filename, "r") as file:
        urls = [line.strip() for line in file]
    return urls

def parse_price(content: str) -> str:
    tree = html.fromstring(content)

    json_text = tree.xpath("string(//pre)")
    data = json.loads(json_text)

    return data["price"]

async def fetch(
        session: aiohttp.ClientSession, 
        url: str,
        semaphore: asyncio.Semaphore,
) -> str:
    async with semaphore:
        async with session.get(url) as response:
            return await response.text()

async def main() -> None:
    urls = load_urls("products.txt")
    semaphore = asyncio.Semaphore(10)

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch(session, url, semaphore) 
            for url in urls
        ]

        results = await asyncio.gather(*tasks)

    print("Получено страниц:", len(results))

    for url, content in zip(urls, results):
        price = parse_price(content)
        print(f"URL: {url}, Price: {price}")


    

if __name__ == "__main__":
    asyncio.run(main())