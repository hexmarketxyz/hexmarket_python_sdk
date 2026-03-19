"""Basic SDK usage: browse events, check balance, read orderbook.

Usage:
    export HEX_API_URL=https://api.hexmarket.io
    python examples/basic.py

For authenticated endpoints, also set:
    export HEX_PUBKEY=<your-solana-pubkey>
    export HEX_API_KEY=<api-key>
    export HEX_SECRET=<base64url-secret>
    export HEX_PASSPHRASE=<passphrase>
"""

import asyncio
import os
from decimal import Decimal

from hexmarket_sdk import HexClient, ApiCredentials


async def main() -> None:
    api_url = os.environ.get("HEX_API_URL", "http://localhost:8080")

    async with HexClient(api_url) as client:
        # --- Public endpoints (no auth) ---

        events = await client.list_events(status="active", limit=5)
        print("=== Active Events ===")
        for item in events:
            print(f"  {item.title} ({len(item.outcomes)} outcomes)")
            for outcome in item.outcomes:
                price_str = (
                    f"{int(outcome.price * 100)}c"
                    if outcome.price is not None
                    else "n/a"
                )
                print(f"    - {outcome.label} @ {price_str}")

        # Orderbook for the first outcome
        if events and events[0].outcomes:
            oid = events[0].outcomes[0].id
            book = await client.get_orderbook(oid)
            print(f"\n=== Orderbook: {events[0].outcomes[0].label} ===")
            print("  Bids:")
            for level in book.bids[:5]:
                print(f"    {level.quantity} @ {level.price}")
            print("  Asks:")
            for level in book.asks[:5]:
                print(f"    {level.quantity} @ {level.price}")

        # Recent trades
        trades = await client.list_trades(limit=5)
        print("\n=== Recent Trades ===")
        for trade in trades:
            print(f"  {trade.side} {trade.outcome_id} @ {trade.price} (qty {trade.quantity})")

        # --- Authenticated endpoints ---

        pubkey = os.environ.get("HEX_PUBKEY")
        api_key = os.environ.get("HEX_API_KEY")
        secret = os.environ.get("HEX_SECRET")
        passphrase = os.environ.get("HEX_PASSPHRASE")

        if all([pubkey, api_key, secret, passphrase]):
            client.set_credentials(
                pubkey,
                ApiCredentials(api_key=api_key, secret=secret, passphrase=passphrase),
            )

            balance = await client.get_balance()
            print(f"\n=== Balance ===")
            print(f"  USDC: {balance.usdc_balance} (locked: {balance.locked_usdc})")

            positions = await client.get_positions()
            print(f"\n=== Positions ===")
            for pos in positions:
                print(f"  outcome={pos.outcome_id} qty={pos.quantity} avg={pos.avg_price}")

            open_orders = await client.get_open_orders()
            print(f"\n=== Open Orders ({len(open_orders)}) ===")
            for order in open_orders[:10]:
                print(
                    f"  {order.id} {order.side} {order.outcome_id} "
                    f"@ {order.price} qty={order.filled_quantity}/{order.quantity}"
                )
        else:
            print(
                "\nSkipping authenticated endpoints "
                "(set HEX_PUBKEY, HEX_API_KEY, HEX_SECRET, HEX_PASSPHRASE)"
            )


if __name__ == "__main__":
    asyncio.run(main())
