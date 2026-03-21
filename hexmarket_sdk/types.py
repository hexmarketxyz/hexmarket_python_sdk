"""API type definitions matching server JSON responses."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Side(str, Enum):
    buy = "buy"
    sell = "sell"


class OrderType(str, Enum):
    limit = "limit"
    market = "market"


class TimeInForce(str, Enum):
    gtc = "gtc"
    ioc = "ioc"
    fok = "fok"


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class PlaceOrderParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    outcome_id: str
    side: Side
    order_type: OrderType = OrderType.limit
    time_in_force: TimeInForce = TimeInForce.gtc
    price: Decimal
    quantity: int
    nonce: int
    signature: str
    client_order_id: Optional[str] = None

    def to_api_dict(self) -> dict:
        d = {
            "outcome_id": self.outcome_id,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "time_in_force": self.time_in_force.value,
            "price": float(self.price),
            "quantity": self.quantity,
            "nonce": self.nonce,
            "signature": self.signature,
        }
        if self.client_order_id is not None:
            d["client_order_id"] = self.client_order_id
        return d


class PlaceOrderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    order_id: str
    status: str
    client_order_id: Optional[str] = None


class Order(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    outcome_id: str
    user_pubkey: str
    side: str
    order_type: str
    time_in_force: str
    price: Decimal
    quantity: int
    filled_quantity: int
    remaining_quantity: int
    status: str
    nonce: int
    signature: str
    created_at: datetime
    updated_at: datetime
    expired_at: Optional[datetime] = None
    client_order_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Trades & Orderbook
# ---------------------------------------------------------------------------


class Trade(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    outcome_id: str
    maker_order_id: str
    taker_order_id: str
    maker_pubkey: str
    taker_pubkey: str
    outcome: Optional[str] = None
    side: str
    price: Decimal
    quantity: int
    maker_fee: int
    taker_fee: int
    settlement_status: str
    settlement_tx: Optional[str] = None
    settled_at: Optional[datetime] = None
    created_at: datetime


class OrderBookLevel(BaseModel):
    price: Decimal
    quantity: int


class OrderBook(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    outcome_id: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: datetime


class MergedOrderBookLevel(BaseModel):
    price: Decimal
    quantity: int
    source: str


class MergedOrderBook(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    outcome_id: str
    bids: list[MergedOrderBookLevel]
    asks: list[MergedOrderBookLevel]
    timestamp: datetime


# ---------------------------------------------------------------------------
# Markets & Events
# ---------------------------------------------------------------------------


class Outcome(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    market_id: str
    label: str
    label_translations: Optional[dict[str, str]] = None
    sort_order: int
    outcome_index: int
    mint: Optional[str] = None
    price: Optional[Decimal] = None
    question: Optional[str] = None
    question_translations: Optional[dict[str, str]] = None
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    outcome: Optional[str] = None
    volume_24h: Optional[Decimal] = None
    total_volume: Optional[Decimal] = None
    liquidity: Optional[Decimal] = None
    close_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class Market(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    event_id: str
    title: str
    title_translations: Optional[dict[str, str]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_url: Optional[str] = None
    market_type: str
    status: str
    start_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    sort_order: int = 0
    onchain_market_id: Optional[int] = None
    pubkey: Optional[str] = None
    vault_pubkey: Optional[str] = None
    collateral_mint: Optional[str] = None
    num_outcomes: int = 0
    price_increment: Optional[Decimal] = None


class Tag(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    slug: str
    label: str
    label_translations: Optional[dict[str, str]] = None
    parent_id: Optional[str] = None
    sort_order: int = 0
    icon_url: Optional[str] = None
    created_at: Optional[datetime] = None


class TagDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    slug: str
    label: str
    label_translations: Optional[dict[str, str]] = None
    parent_id: Optional[str] = None
    sort_order: int = 0
    icon_url: Optional[str] = None
    created_at: Optional[datetime] = None
    children: list[Tag] = []


class HexEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    slug: str
    title: str
    title_translations: Optional[dict[str, str]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_url: Optional[str] = None
    status: str
    close_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_archived: Optional[bool] = None


class MarketDetail(BaseModel):
    """A market with its nested outcomes."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    event_id: str
    title: str
    title_translations: Optional[dict[str, str]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_url: Optional[str] = None
    market_type: str
    status: str
    start_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    sort_order: int = 0
    onchain_market_id: Optional[int] = None
    pubkey: Optional[str] = None
    vault_pubkey: Optional[str] = None
    collateral_mint: Optional[str] = None
    num_outcomes: int = 0
    price_increment: Optional[Decimal] = None
    outcomes: list[Outcome] = []


class EventListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    slug: str
    title: str
    title_translations: Optional[dict[str, str]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_url: Optional[str] = None
    status: str
    close_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_archived: Optional[bool] = None
    markets: list[MarketDetail] = []
    tags: list[Tag] = []


class EventDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    slug: str
    title: str
    title_translations: Optional[dict[str, str]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_url: Optional[str] = None
    status: str
    close_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_archived: Optional[bool] = None
    markets: list[MarketDetail] = []
    tags: list[Tag] = []


# ---------------------------------------------------------------------------
# Balances & Positions
# ---------------------------------------------------------------------------


class Position(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_pubkey: str
    outcome_id: str
    quantity: int
    avg_price: Optional[Decimal] = None
    updated_at: Optional[datetime] = None


class UserBalance(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_pubkey: str
    usdc_balance: int
    locked_usdc: int
    updated_at: Optional[datetime] = None


class VaultBalance(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user: str
    vault_pubkey: str
    usdc_balance: int


class PriceSnapshot(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    outcome_id: str
    price: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    captured_at: datetime


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------


class TransactionResponse(BaseModel):
    transaction: str


class SubmitResponse(BaseModel):
    signature: str
