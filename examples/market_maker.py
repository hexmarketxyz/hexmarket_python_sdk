"""Simple market-making example.

Posts symmetric bid/ask quotes around the current mid price
and refreshes them periodically.

Usage:
    export HEX_API_URL=https://api.hexmarket.xyz
    export HEX_PUBKEY=<your-solana-pubkey>
    export HEX_API_KEY=<api-key>
    export HEX_SECRET=<base64url-secret>
    export HEX_PASSPHRASE=<passphrase>
    export HEX_SECRET_KEY=<base58-encoded-32-byte-ed25519-secret-key>
    export HEX_OUTCOME_ID=<outcome-uuid>
    python examples/market_maker.py
"""

import asyncio
import os
from decimal import Decimal

import base58

from hexmarket_sdk import (
    ApiCredentials,
    HexClient,
    PlaceOrderParams,
    Side,
    OrderType,
    TimeInForce,
    build_order_message,
    ed25519_sign,
    generate_nonce,
)


SPREAD = Decimal("0.02")  # 2 cents
QTY = 5
REFRESH_INTERVAL = 10  # seconds


async def main() -> None:
    api_url = os.environ.get("HEX_API_URL", "http://localhost:8080")
    pubkey = os.environ["HEX_PUBKEY"]
    api_key = os.environ["HEX_API_KEY"]
    secret = os.environ["HEX_SECRET"]
    passphrase = os.environ["HEX_PASSPHRASE"]
    secret_key_b58 = os.environ["HEX_SECRET_KEY"]
    outcome_id = os.environ["HEX_OUTCOME_ID"]

    secret_key_bytes = base58.b58decode(secret_key_b58)[:32]

    async with HexClient(api_url) as client:
        client.set_credentials(
            pubkey,
            ApiCredentials(api_key=api_key, secret=secret, passphrase=passphrase),
        )

        while True:
            try:
                # 1. Get current orderbook
                book = await client.get_orderbook(outcome_id)

                best_bid = book.bids[0].price if book.bids else None
                best_ask = book.asks[0].price if book.asks else None

                if best_bid is not None and best_ask is not None:
                    mid = (best_bid + best_ask) / 2
                elif best_bid is not None:
                    mid = best_bid + SPREAD / 2
                elif best_ask is not None:
                    mid = best_ask - SPREAD / 2
                else:
                    mid = Decimal("0.50")

                bid_price = max(mid - SPREAD / 2, Decimal("0.01"))
                ask_price = min(mid + SPREAD / 2, Decimal("0.99"))

                print(f"mid={mid} bid={bid_price} ask={ask_price} qty={QTY}")

                # 2. Cancel existing open orders
                open_orders = await client.get_open_orders(outcome_id)
                for order in open_orders:
                    try:
                        await client.cancel_order(order.id)
                    except Exception as e:
                        print(f"cancel failed: {e}")

                # 3. Place bid
                nonce = generate_nonce()
                msg = build_order_message(outcome_id, "buy", str(bid_price), QTY, nonce)
                sig = ed25519_sign(secret_key_bytes, msg)

                try:
                    resp = await client.place_order(
                        PlaceOrderParams(
                            outcome_id=outcome_id,
                            side=Side.buy,
                            order_type=OrderType.limit,
                            time_in_force=TimeInForce.gtc,
                            price=bid_price,
                            quantity=QTY,
                            nonce=nonce,
                            signature=sig,
                        )
                    )
                    print(f"BID placed: {resp.order_id}")
                except Exception as e:
                    print(f"BID failed: {e}")

                # 4. Place ask
                nonce = generate_nonce()
                msg = build_order_message(outcome_id, "sell", str(ask_price), QTY, nonce)
                sig = ed25519_sign(secret_key_bytes, msg)

                try:
                    resp = await client.place_order(
                        PlaceOrderParams(
                            outcome_id=outcome_id,
                            side=Side.sell,
                            order_type=OrderType.limit,
                            time_in_force=TimeInForce.gtc,
                            price=ask_price,
                            quantity=QTY,
                            nonce=nonce,
                            signature=sig,
                        )
                    )
                    print(f"ASK placed: {resp.order_id}")
                except Exception as e:
                    print(f"ASK failed: {e}")

            except Exception as e:
                print(f"Error: {e}")

            # 5. Wait before refreshing
            await asyncio.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
