"""WebSocket clients for real-time market data and user events.

Two WebSocket endpoints are available:

- ``/ws/market`` — public market data (order books, trades, prices).
  Subscribe by outcome (asset) IDs, no authentication required.
- ``/ws/user`` — private user events (order fills, cancellations).
  Requires L2 API key authentication.

Example — Market WebSocket::

    from hexmarket_sdk.ws import HexMarketWs

    async with HexMarketWs("wss://api.hexmarket.xyz/ws/market") as ws:
        await ws.subscribe(["outcome-id-1", "outcome-id-2"])
        async for event in ws:
            print(event["event_type"], event["asset_id"])

Example — User WebSocket::

    from hexmarket_sdk.ws import HexUserWs
    from hexmarket_sdk import ApiCredentials

    creds = ApiCredentials(
        api_key="your-api-key",
        secret="your-secret",
        passphrase="your-passphrase",
    )

    async with HexUserWs("wss://api.hexmarket.xyz/ws/user", creds) as ws:
        async for event in ws:
            print(event)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import websockets
from websockets.asyncio.client import ClientConnection

from hexmarket_sdk.auth import ApiCredentials


class HexMarketWs:
    """Public market data WebSocket client (``/ws/market``).

    Subscribes by outcome (asset) IDs. No authentication required.
    Supports async iteration and async context manager.
    """

    def __init__(self, url: str, *, ping_interval: float = 10.0):
        self._url = url
        self._ping_interval = ping_interval
        self._ws: ClientConnection | None = None
        self._ping_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        """Open the WebSocket connection."""
        self._ws = await websockets.connect(self._url)
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def __aenter__(self) -> HexMarketWs:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def subscribe(self, asset_ids: list[str]) -> None:
        """Send the initial subscription for the given outcome (asset) IDs."""
        await self._send({"assets_ids": asset_ids, "type": "market"})

    async def subscribe_more(self, asset_ids: list[str]) -> None:
        """Dynamically subscribe to additional asset IDs."""
        await self._send({"operation": "subscribe", "assets_ids": asset_ids})

    async def unsubscribe(self, asset_ids: list[str]) -> None:
        """Unsubscribe from asset IDs."""
        await self._send({"operation": "unsubscribe", "assets_ids": asset_ids})

    async def recv(self) -> dict[str, Any]:
        """Receive the next market event, skipping PONG heartbeats."""
        while True:
            assert self._ws is not None, "Not connected"
            raw = await self._ws.recv()
            text = raw if isinstance(raw, str) else raw.decode()
            if text == "PONG":
                continue
            return json.loads(text)

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self

    async def __anext__(self) -> dict[str, Any]:
        try:
            return await self.recv()
        except websockets.ConnectionClosed:
            raise StopAsyncIteration

    async def _send(self, data: dict[str, Any]) -> None:
        assert self._ws is not None, "Not connected"
        await self._ws.send(json.dumps(data))

    async def _ping_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._ping_interval)
                if self._ws:
                    await self._ws.send("PING")
        except (asyncio.CancelledError, websockets.ConnectionClosed):
            pass


class HexUserWs:
    """Authenticated user WebSocket client (``/ws/user``).

    Requires L2 API key credentials. Receives order lifecycle events.
    Supports async iteration and async context manager.
    """

    def __init__(
        self,
        url: str,
        credentials: ApiCredentials,
        markets: list[str] | None = None,
        *,
        ping_interval: float = 10.0,
    ):
        self._url = url
        self._credentials = credentials
        self._markets = markets or []
        self._ping_interval = ping_interval
        self._ws: ClientConnection | None = None
        self._ping_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        """Open the WebSocket connection and send L2 auth credentials."""
        self._ws = await websockets.connect(self._url)
        self._ping_task = asyncio.create_task(self._ping_loop())

        auth_msg = {
            "auth": {
                "apiKey": self._credentials.api_key,
                "secret": self._credentials.secret,
                "passphrase": self._credentials.passphrase,
            },
            "type": "user",
            "markets": self._markets,
        }
        await self._ws.send(json.dumps(auth_msg))

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def __aenter__(self) -> HexUserWs:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def subscribe_markets(self, markets: list[str]) -> None:
        """Dynamically subscribe to additional markets."""
        await self._send({"operation": "subscribe", "markets": markets})

    async def unsubscribe_markets(self, markets: list[str]) -> None:
        """Dynamically unsubscribe from markets."""
        await self._send({"operation": "unsubscribe", "markets": markets})

    async def recv(self) -> dict[str, Any]:
        """Receive the next user event, skipping PONG heartbeats."""
        while True:
            assert self._ws is not None, "Not connected"
            raw = await self._ws.recv()
            text = raw if isinstance(raw, str) else raw.decode()
            if text == "PONG":
                continue
            return json.loads(text)

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self

    async def __anext__(self) -> dict[str, Any]:
        try:
            return await self.recv()
        except websockets.ConnectionClosed:
            raise StopAsyncIteration

    async def _send(self, data: dict[str, Any]) -> None:
        assert self._ws is not None, "Not connected"
        await self._ws.send(json.dumps(data))

    async def _ping_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._ping_interval)
                if self._ws:
                    await self._ws.send("PING")
        except (asyncio.CancelledError, websockets.ConnectionClosed):
            pass
