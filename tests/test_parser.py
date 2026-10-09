from decimal import Decimal

import asyncio
import unittest
from unittest.mock import AsyncMock

import pytest

from src.price_parser import parser
from src.price_parser.parser import parse_price

import aiohttp
from unittest.mock import AsyncMock, MagicMock


def test_parse_price_returns_price():
    content = """
    <html>
        <body>
            <pre>{
                "id": 1,
                "title": "Test product",
                "price": 155.62
            }</pre>
        </body>
    </html>
    """

    result = parse_price(content)

    assert result == Decimal("155.62")

def test_parse_price_without_json():
    content = "<html><body><h1>Product not found</h1></body></html>"

    with pytest.raises(
        ValueError,
        match="На странице не найден JSON с данными товара",
    ):
        parse_price(content)

def test_parse_price_without_price_field():
    content = """
    <html>
        <body>
            <pre>{"id": 1, "title": "Test product"}</pre>
        </body>
    </html>
    """

    with pytest.raises(
        ValueError,
        match="Цена отсутствует или имеет неверный формат",
    ):
        parse_price(content)


def test_parse_price_with_string_value():
    content = """
    <html>
        <body>
            <pre>{"id": 1, "price": "unknown"}</pre>
        </body>
    </html>
    """

    with pytest.raises(
        ValueError,
        match="Цена отсутствует или имеет неверный формат",
    ):
        parse_price(content)


def test_parse_price_with_negative_value():
    content = """
    <html>
        <body>
            <pre>{"id": 1, "price": -10}</pre>
        </body>
    </html>
    """

    with pytest.raises(
        ValueError,
        match="Цена не может быть отрицательной",
    ):
        parse_price(content)

def test_process_product_handles_fetch_error(monkeypatch):
    async def run_test():
        session = AsyncMock()
        semaphore = asyncio.Semaphore(1)
        storage = AsyncMock()

        async def fake_fetch(
                session, 
                url, 
                semaphore,
                storage,
            ):
            raise RuntimeError("Connection failed")

        monkeypatch.setattr(parser, "fetch", fake_fetch)

        result = await parser.process_product(
            session,
            "https://example.com/product/1",
            semaphore,
            storage,
        )

        assert result is False

    asyncio.run(run_test())

def test_process_product_succeeds(monkeypatch):
    async def run_test():
        session = AsyncMock()
        semaphore = asyncio.Semaphore(1)
        storage = AsyncMock()

        async def fake_fetch(
                session, 
                url, 
                semaphore,
            ):
            return """
            <html><body>
                <pre>{"id": 1, "price": 123.45}</pre>
            </body></html>
            """

        monkeypatch.setattr(parser, "fetch", fake_fetch)

        result = await parser.process_product(
            session,
            "https://example.com/product/1",
            semaphore,
            storage,
        )
    
        assert result is True

    asyncio.run(run_test())

def test_fetch_does_not_retry_404():
    async def run_test():
        session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        response = MagicMock()
        response.status = 404
        response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
        )

        request_context = MagicMock()
        request_context.__aenter__ = AsyncMock(return_value=response)
        request_context.__aexit__ = AsyncMock(return_value=False)
        session.get.return_value = request_context

        with pytest.raises(aiohttp.ClientResponseError) as exc_info:
            await parser.fetch(
                session,
                "https://example.com/product/404",
                semaphore,
            )

        assert exc_info.value.status == 404
        assert session.get.call_count == 1

    asyncio.run(run_test())

def test_fetch_retries_on_503(monkeypatch):
    async def run_test():
        session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        response_503 = MagicMock()
        response_503.status = 503
        response_503.headers = {}
        response_503.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=503,
        )

        response_200 = MagicMock()
        response_200.status = 200
        response_200.text = AsyncMock(return_value="page content")

        def make_context(response):
            context = MagicMock()
            context.__aenter__ = AsyncMock(return_value=response)
            context.__aexit__ = AsyncMock(return_value=False)
            return context

        session.get.side_effect = [
            make_context(response_503),
            make_context(response_200),
        ]

        sleep_mock = AsyncMock()
        monkeypatch.setattr(parser.asyncio, "sleep", sleep_mock)

        result = await parser.fetch(
            session,
            "https://example.com/product/1",
            semaphore,
        )

        assert result == "page content"
        assert session.get.call_count == 2
        sleep_mock.assert_awaited_once_with(1)

    asyncio.run(run_test())

def test_fetch_stops_after_max_attempts(monkeypatch):
    async def run_test():
        session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        response = MagicMock()
        response.status = 503
        response.headers = {}
        response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=503,
        )

        def make_context():
            context = MagicMock()
            context.__aenter__ = AsyncMock(return_value=response)
            context.__aexit__ = AsyncMock(return_value=False)
            return context

        session.get.side_effect = [
            make_context(),
            make_context(),
            make_context(),
        ]

        sleep_mock = AsyncMock()
        monkeypatch.setattr(parser.asyncio, "sleep", sleep_mock)

        with pytest.raises(aiohttp.ClientResponseError) as exc_info:
            await parser.fetch(
                session,
                "https://example.com/product/1",
                semaphore,
            )

        assert exc_info.value.status == 503
        assert session.get.call_count == 3
        assert sleep_mock.await_args_list == [
            unittest.mock.call(1),
            unittest.mock.call(2),
        ]

    asyncio.run(run_test())

def test_process_product_saves_price(monkeypatch):
    async def run_test():
        session = AsyncMock()
        semaphore = asyncio.Semaphore(1)
        storage = AsyncMock()

        async def fake_fetch(session, url, semaphore):
            return """
            <html><body>
                <pre>{"id": 42, "price": 123.45}</pre>
            </body></html>
            """

        monkeypatch.setattr(parser, "fetch", fake_fetch)

        result = await parser.process_product(
            session,
            "https://example.com/product/42",
            semaphore,
            storage,
        )

        assert result is True
        storage.save_price.assert_awaited_once_with(42, Decimal("123.45"))

    asyncio.run(run_test())

def test_process_product_does_not_save_price_on_fetch_error(monkeypatch):
    async def run_test():
        session = AsyncMock()
        semaphore = asyncio.Semaphore(1)
        storage = AsyncMock()

        async def fake_fetch(session, url, semaphore):
            raise RuntimeError("Connection failed")

        monkeypatch.setattr(parser, "fetch", fake_fetch)

        result = await parser.process_product(
            session,
            "https://example.com/product/42",
            semaphore,
            storage,
        )

        assert result is False
        storage.save_price.assert_not_awaited()

    asyncio.run(run_test())