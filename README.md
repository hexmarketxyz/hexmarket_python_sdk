# HexMarket Python SDK

Python client for the [HexMarket](https://hexmarket.io) prediction market API. Built for quantitative trading and market making.

## Installation

```bash
pip install git+https://github.com/hexmarketxyz/hexmarket_python_sdk.git
```

**Requirements:** Python 3.10+

## Quick Start

```python
import asyncio
from hexmarket_sdk import HexClient, ApiCredentials

async def main():
    async with HexClient("https://api.hexmarket.io") as client:
        # Browse markets (no auth needed)
        events = await client.list_events(status="active", limit=10)
        for event in events:
            print(f"{event.title} — {len(event.outcomes)} outcomes")

        # Read orderbook
        outcome_id = events[0].outcomes[0].id
        book = await client.get_orderbook(outcome_id)
        print(f"Best bid: {book.bids[0].price}, Best ask: {book.asks[0].price}")

        # Authenticate for trading
        client.set_credentials(
            pubkey="YourSolanaPubkey",
            credentials=ApiCredentials(
                api_key="your-api-key",
                secret="your-base64url-secret",
                passphrase="your-passphrase",
            ),
        )

        balance = await client.get_balance()
        print(f"USDC: {balance.usdc_balance} (locked: {balance.locked_usdc})")

asyncio.run(main())
```

## Authentication

HexMarket uses two authentication layers:

| Layer | Mechanism | Used For |
|-------|-----------|----------|
| **L1** | Ed25519 wallet signature | API key creation |
| **L2** | HMAC-SHA256 with API credentials | All trading endpoints |

For trading, you need API credentials (`api_key`, `secret`, `passphrase`). Create them once via the HexMarket web UI, then pass to `client.set_credentials()` — the SDK handles HMAC signing automatically.

## Placing Orders

Each order requires an Ed25519 wallet signature for on-chain settlement:

```python
from hexmarket_sdk import (
    HexClient, ApiCredentials, PlaceOrderParams,
    Side, OrderType, TimeInForce,
    build_order_message, ed25519_sign, generate_nonce,
)
from decimal import Decimal
import base58

# Your 32-byte Ed25519 secret key
secret_key = base58.b58decode("YourBase58SecretKey")[:32]

async with HexClient("https://api.hexmarket.io") as client:
    client.set_credentials("YourPubkey", ApiCredentials(...))

    nonce = generate_nonce()
    msg = build_order_message("outcome-uuid", "buy", "0.55", 10, nonce)
    sig = ed25519_sign(secret_key, msg)

    resp = await client.place_order(PlaceOrderParams(
        outcome_id="outcome-uuid",
        side=Side.buy,
        price=Decimal("0.55"),
        quantity=10,
        nonce=nonce,
        signature=sig,
    ))
    print(f"Order placed: {resp.order_id}")
```

## API Reference

### Public Endpoints (no auth)

| Method | Description |
|--------|-------------|
| `list_events(tag, status, limit, offset)` | List prediction events |
| `get_event(slug)` | Get event detail by slug |
| `list_markets(status, category, limit, offset)` | List outcomes |
| `get_market(outcome_id)` | Get single outcome |
| `get_orderbook(outcome_id)` | Get orderbook (bids/asks) |
| `get_merged_orderbook(outcome_id)` | Orderbook with cross-outcome liquidity |
| `list_trades(outcome_id, user, limit)` | List trades |
| `get_price_snapshots(outcome_id, from_time, to_time, limit)` | Price history |
| `list_tags()` | List categories |
| `get_tag(slug)` | Get category with children |

### Authenticated Endpoints (L2 auth)

| Method | Description |
|--------|-------------|
| `place_order(params)` | Place a limit/market order |
| `cancel_order(order_id)` | Cancel an open order |
| `get_open_orders(outcome_id?)` | List open orders |
| `get_closed_orders(outcome_id?)` | List filled/cancelled orders |
| `get_balance()` | USDC balance and locked amount |
| `get_positions()` | Outcome token positions |
| `get_vault_balance()` | On-chain vault USDC balance |
| `create_vault()` | Create user vault |
| `deposit(amount)` | Build deposit transaction |
| `withdraw(amount)` | Build withdrawal transaction |
| `submit_transaction(tx_b64)` | Submit signed Solana transaction |

## Examples

- [`examples/basic.py`](examples/basic.py) — Browse events, check balance, read orderbook
- [`examples/market_maker.py`](examples/market_maker.py) — Symmetric bid/ask quoting loop

## Dependencies

- [httpx](https://www.python-httpx.org/) — Async HTTP client
- [pydantic](https://docs.pydantic.dev/) — Type-safe response models
- [PyNaCl](https://pynacl.readthedocs.io/) — Ed25519 signing
- [base58](https://pypi.org/project/base58/) — Solana address encoding

## License

MIT
