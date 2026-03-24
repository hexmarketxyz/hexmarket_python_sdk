"""HexMarket API client."""

from __future__ import annotations

import json
from typing import Any

import httpx

from hexmarket_sdk.auth import ApiCredentials, build_l2_headers
from hexmarket_sdk.types import (
    BatchUpdateResponse,
    EventDetail,
    EventListItem,
    MergedOrderBook,
    Order,
    OrderBook,
    Outcome,
    PlaceOrderParams,
    PlaceOrderResponse,
    Position,
    PriceSnapshot,
    SubmitResponse,
    Tag,
    TagDetail,
    Trade,
    TransactionResponse,
    UserBalance,
    VaultBalance,
)


class HexClientError(Exception):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"API error ({status}): {message}")


class HexClient:
    """HexMarket API client.

    Example::

        from hexmarket_sdk import HexClient, ApiCredentials

        client = HexClient("https://api.hexmarket.xyz")

        # Public endpoints (no auth)
        events = await client.list_events(status="active", limit=5)

        # Set credentials for authenticated endpoints
        client.set_credentials(
            pubkey="YourSolanaPubkey",
            credentials=ApiCredentials(
                api_key="your-api-key",
                secret="your-base64url-secret",
                passphrase="your-passphrase",
            ),
        )

        balance = await client.get_balance()
        print(f"USDC: {balance.usdc_balance}")

    All methods are async. Use ``async with`` or call ``await client.close()``
    when done to release the underlying connection pool.
    """

    def __init__(self, api_url: str = "http://localhost:8080", *, timeout: float = 30.0):
        self._base_url = api_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)
        self._pubkey: str | None = None
        self._credentials: ApiCredentials | None = None

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> HexClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ---------------------------------------------------------------------------
    # Credentials
    # ---------------------------------------------------------------------------

    def set_credentials(self, pubkey: str, credentials: ApiCredentials) -> None:
        """Set API credentials for L2-authenticated endpoints."""
        self._pubkey = pubkey
        self._credentials = credentials

    def clear_credentials(self) -> None:
        self._pubkey = None
        self._credentials = None

    def _require_auth(self) -> tuple[str, ApiCredentials]:
        if self._pubkey is None or self._credentials is None:
            raise HexClientError(0, "Missing credentials — call set_credentials() first")
        return self._pubkey, self._credentials

    def _l2_headers(self, method: str, path: str, body: str | None = None) -> dict[str, str]:
        pubkey, creds = self._require_auth()
        return build_l2_headers(creds, pubkey, method, path, body)

    # ---------------------------------------------------------------------------
    # Response handling
    # ---------------------------------------------------------------------------

    @staticmethod
    def _check(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            raise HexClientError(resp.status_code, resp.text)

    # ---------------------------------------------------------------------------
    # Markets
    # ---------------------------------------------------------------------------

    async def list_markets(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Outcome]:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if category:
            params["category"] = category
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        resp = await self._http.get("/api/v1/markets", params=params)
        self._check(resp)
        return [Outcome.model_validate(o) for o in resp.json()]

    async def get_market(self, outcome_id: str) -> Outcome:
        resp = await self._http.get(f"/api/v1/markets/{outcome_id}")
        self._check(resp)
        return Outcome.model_validate(resp.json())

    # ---------------------------------------------------------------------------
    # Events
    # ---------------------------------------------------------------------------

    async def list_events(
        self,
        *,
        tag: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EventListItem]:
        params: dict[str, Any] = {}
        if tag:
            params["tag"] = tag
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        resp = await self._http.get("/api/v1/events", params=params)
        self._check(resp)
        return [EventListItem.model_validate(e) for e in resp.json()]

    async def get_event(self, slug: str) -> EventDetail:
        resp = await self._http.get(f"/api/v1/events/{slug}")
        self._check(resp)
        return EventDetail.model_validate(resp.json())

    # ---------------------------------------------------------------------------
    # Tags
    # ---------------------------------------------------------------------------

    async def list_tags(self) -> list[Tag]:
        resp = await self._http.get("/api/v1/tags")
        self._check(resp)
        return [Tag.model_validate(t) for t in resp.json()]

    async def get_tag(self, slug: str) -> TagDetail:
        resp = await self._http.get(f"/api/v1/tags/{slug}")
        self._check(resp)
        return TagDetail.model_validate(resp.json())

    # ---------------------------------------------------------------------------
    # Orderbook
    # ---------------------------------------------------------------------------

    async def get_orderbook(self, outcome_id: str) -> OrderBook:
        resp = await self._http.get(f"/api/v1/orderbook/{outcome_id}")
        self._check(resp)
        return OrderBook.model_validate(resp.json())

    async def get_merged_orderbook(self, outcome_id: str) -> MergedOrderBook:
        resp = await self._http.get(f"/api/v1/orderbook/{outcome_id}/merged")
        self._check(resp)
        return MergedOrderBook.model_validate(resp.json())

    # ---------------------------------------------------------------------------
    # Trades
    # ---------------------------------------------------------------------------

    async def list_trades(
        self,
        *,
        outcome_id: str | None = None,
        user: str | None = None,
        limit: int | None = None,
    ) -> list[Trade]:
        params: dict[str, Any] = {}
        if outcome_id:
            params["outcome_id"] = outcome_id
        if user:
            params["user"] = user
        if limit is not None:
            params["limit"] = limit

        resp = await self._http.get("/api/v1/trades", params=params)
        self._check(resp)
        return [Trade.model_validate(t) for t in resp.json()]

    # ---------------------------------------------------------------------------
    # Price Snapshots
    # ---------------------------------------------------------------------------

    async def get_price_snapshots(
        self,
        outcome_id: str,
        *,
        from_time: str | None = None,
        to_time: str | None = None,
        limit: int | None = None,
    ) -> list[PriceSnapshot]:
        params: dict[str, Any] = {"outcome_id": outcome_id}
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        if limit is not None:
            params["limit"] = limit

        resp = await self._http.get("/api/v1/price-snapshots", params=params)
        self._check(resp)
        return [PriceSnapshot.model_validate(s) for s in resp.json()]

    # ---------------------------------------------------------------------------
    # Orders (L2 auth required)
    # ---------------------------------------------------------------------------

    async def place_order(self, params: PlaceOrderParams) -> PlaceOrderResponse:
        path = "/api/v1/orders"
        body = json.dumps(params.to_api_dict())
        headers = self._l2_headers("POST", path)
        headers["Content-Type"] = "application/json"

        resp = await self._http.post(path, content=body, headers=headers)
        self._check(resp)
        return PlaceOrderResponse.model_validate(resp.json())

    async def batch_place_orders(
        self,
        market_id: str,
        orders: list[PlaceOrderParams],
    ) -> dict:
        """Place multiple orders in a single batch.

        All orders must belong to the same market.
        Returns ``{"results": [{"index": 0, "order_id": "...", "status": "accepted"}, ...]}``.
        """
        path = "/api/v1/orders/batch"
        body = json.dumps({
            "market_id": market_id,
            "orders": [o.to_api_dict() for o in orders],
        })
        headers = self._l2_headers("POST", path)
        headers["Content-Type"] = "application/json"

        resp = await self._http.post(path, content=body, headers=headers)
        self._check(resp)
        return resp.json()

    async def batch_cancel_orders(
        self,
        market_id: str,
        order_ids: list[str] | None = None,
        client_order_ids: list[str] | None = None,
    ) -> dict:
        """Cancel multiple orders in a single batch.

        All orders must belong to the same market.
        Supports cancellation by ``order_ids`` and/or ``client_order_ids``.
        Returns ``{"results": [{"order_id": "...", "status": "cancelled"}, ...]}``.
        """
        path = "/api/v1/orders/batch"
        payload: dict = {"market_id": market_id}
        if order_ids:
            payload["order_ids"] = order_ids
        if client_order_ids:
            payload["client_order_ids"] = client_order_ids
        body = json.dumps(payload)
        headers = self._l2_headers("DELETE", path)
        headers["Content-Type"] = "application/json"

        resp = await self._http.request("DELETE", path, content=body, headers=headers)
        self._check(resp)
        return resp.json()

    async def batch_update_orders(
        self,
        market_id: str,
        cancel_order_ids: list[str] | None = None,
        cancel_client_order_ids: list[str] | None = None,
        place_orders: list[PlaceOrderParams] | None = None,
    ) -> BatchUpdateResponse:
        """Cancel and place orders in a single atomic batch.

        All orders must belong to the same market.
        Returns a ``BatchUpdateResponse`` with ``cancel_results`` and ``place_results``.
        """
        path = "/api/v1/orders/batch"
        payload: dict = {"market_id": market_id}
        if cancel_order_ids:
            payload["cancel_order_ids"] = cancel_order_ids
        if cancel_client_order_ids:
            payload["cancel_client_order_ids"] = cancel_client_order_ids
        if place_orders:
            payload["place_orders"] = [o.to_api_dict() for o in place_orders]
        body = json.dumps(payload)
        headers = self._l2_headers("PUT", path)
        headers["Content-Type"] = "application/json"

        resp = await self._http.put(path, content=body, headers=headers)
        self._check(resp)
        return BatchUpdateResponse.model_validate(resp.json())

    async def get_order_by_client_id(self, client_order_id: str) -> Order:
        """Get an order by client_order_id (requires L2 auth)."""
        path = f"/api/v1/orders/client/{client_order_id}"
        headers = self._l2_headers("GET", path)
        resp = await self._http.get(path, headers=headers)
        self._check(resp)
        return Order.model_validate(resp.json())

    async def cancel_order_by_client_id(self, client_order_id: str) -> dict:
        """Cancel an order by client_order_id (requires L2 auth)."""
        path = f"/api/v1/orders/client/{client_order_id}"
        headers = self._l2_headers("DELETE", path)
        resp = await self._http.delete(path, headers=headers)
        self._check(resp)
        return resp.json()

    async def cancel_order(self, order_id: str) -> dict:
        path = f"/api/v1/orders/{order_id}"
        headers = self._l2_headers("DELETE", path)

        resp = await self._http.delete(path, headers=headers)
        self._check(resp)
        return resp.json()

    async def cancel_all_orders(
        self,
        *,
        market_id: str | None = None,
        event_id: str | None = None,
    ) -> dict:
        """Cancel all open orders, optionally filtered by market or event.

        Returns ``{"cancelled_count": N, "status": "cancelled", "orders": [{"order_id": "...", "client_order_id": "..."}]}``.
        """
        params: dict[str, Any] = {}
        if market_id:
            params["market_id"] = market_id
        if event_id:
            params["event_id"] = event_id

        path = "/api/v1/orders"
        headers = self._l2_headers("DELETE", path)
        resp = await self._http.delete(path, params=params, headers=headers)
        self._check(resp)
        return resp.json()

    async def get_open_orders(self, outcome_id: str | None = None) -> list[Order]:
        pubkey, _ = self._require_auth()
        path = f"/api/v1/orders?user={pubkey}&status=open"
        if outcome_id:
            path += f"&outcome_id={outcome_id}"

        headers = self._l2_headers("GET", path)
        resp = await self._http.get(path, headers=headers)
        self._check(resp)
        return [Order.model_validate(o) for o in resp.json()]

    async def get_closed_orders(self, outcome_id: str | None = None) -> list[Order]:
        pubkey, _ = self._require_auth()
        path = f"/api/v1/orders?user={pubkey}&status=closed"
        if outcome_id:
            path += f"&outcome_id={outcome_id}"

        headers = self._l2_headers("GET", path)
        resp = await self._http.get(path, headers=headers)
        self._check(resp)
        return [Order.model_validate(o) for o in resp.json()]

    # ---------------------------------------------------------------------------
    # Balances (L2 auth required)
    # ---------------------------------------------------------------------------

    async def get_balance(self) -> UserBalance:
        pubkey, _ = self._require_auth()
        path = f"/api/v1/balances?user={pubkey}"
        headers = self._l2_headers("GET", path)

        resp = await self._http.get(path, headers=headers)
        self._check(resp)
        return UserBalance.model_validate(resp.json())

    # ---------------------------------------------------------------------------
    # Positions (L2 auth required)
    # ---------------------------------------------------------------------------

    async def get_positions(self) -> list[Position]:
        pubkey, _ = self._require_auth()
        path = f"/api/v1/positions?user={pubkey}"
        headers = self._l2_headers("GET", path)

        resp = await self._http.get(path, headers=headers)
        self._check(resp)
        return [Position.model_validate(p) for p in resp.json()]

    # ---------------------------------------------------------------------------
    # Vault (L2 auth required)
    # ---------------------------------------------------------------------------

    async def create_vault(self) -> TransactionResponse:
        path = "/api/v1/vault/create"
        headers = self._l2_headers("POST", path)
        headers["Content-Type"] = "application/json"

        resp = await self._http.post(path, headers=headers)
        self._check(resp)
        return TransactionResponse.model_validate(resp.json())

    async def deposit(self, amount: int) -> TransactionResponse:
        """Build a deposit transaction. ``amount`` is in USDC base units (6 decimals)."""
        path = "/api/v1/vault/deposit"
        body = json.dumps({"amount": amount})
        headers = self._l2_headers("POST", path)
        headers["Content-Type"] = "application/json"

        resp = await self._http.post(path, content=body, headers=headers)
        self._check(resp)
        return TransactionResponse.model_validate(resp.json())

    async def withdraw(self, amount: int) -> TransactionResponse:
        """Build a withdrawal transaction. ``amount`` is in USDC base units (6 decimals)."""
        path = "/api/v1/vault/withdraw"
        body = json.dumps({"amount": amount})
        headers = self._l2_headers("POST", path)
        headers["Content-Type"] = "application/json"

        resp = await self._http.post(path, content=body, headers=headers)
        self._check(resp)
        return TransactionResponse.model_validate(resp.json())

    async def submit_transaction(self, transaction_b64: str) -> SubmitResponse:
        """Submit a fully-signed Solana transaction."""
        path = "/api/v1/vault/submit"
        body = json.dumps({"transaction": transaction_b64})
        headers = self._l2_headers("POST", path)
        headers["Content-Type"] = "application/json"

        resp = await self._http.post(path, content=body, headers=headers)
        self._check(resp)
        return SubmitResponse.model_validate(resp.json())

    async def get_vault_balance(self) -> VaultBalance:
        pubkey, _ = self._require_auth()
        path = f"/api/v1/vault/balance?user={pubkey}"
        headers = self._l2_headers("GET", path)

        resp = await self._http.get(path, headers=headers)
        self._check(resp)
        return VaultBalance.model_validate(resp.json())
