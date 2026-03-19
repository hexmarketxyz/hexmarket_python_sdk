"""L1 (wallet) and L2 (API key HMAC) authentication for HexMarket."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import random
from dataclasses import dataclass

from nacl.signing import SigningKey


@dataclass
class ApiCredentials:
    """Stored API credentials returned by ``POST /auth/api-key``."""

    api_key: str
    secret: str  # base64url-encoded HMAC secret
    passphrase: str


# ---------------------------------------------------------------------------
# L2 HMAC signing
# ---------------------------------------------------------------------------

def _base64url_decode(s: str) -> bytes:
    """Decode base64url (with or without padding)."""
    s = s.replace("-", "+").replace("_", "/")
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.b64decode(s)


def _base64url_encode_nopad(data: bytes) -> str:
    """Encode bytes as base64url without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def build_l2_signing_payload(
    timestamp: int,
    method: str,
    path: str,
    body: str | None = None,
) -> str:
    """Build the HMAC-SHA256 payload: ``{timestamp}{METHOD}{path}[{body}]``."""
    payload = f"{timestamp}{method}{path}"
    if body:
        payload += body
    return payload


def sign_l2(secret_b64: str, payload: str) -> str:
    """Sign a payload with the API secret using HMAC-SHA256.

    Returns a base64url-encoded (no padding) signature.
    """
    secret_bytes = _base64url_decode(secret_b64)
    sig = hmac.new(secret_bytes, payload.encode(), hashlib.sha256).digest()
    return _base64url_encode_nopad(sig)


def build_l2_headers(
    creds: ApiCredentials,
    pubkey: str,
    method: str,
    path: str,
    body: str | None = None,
) -> dict[str, str]:
    """Build L2 authentication headers for an API request.

    Args:
        creds: API credentials (api_key, secret, passphrase).
        pubkey: Solana pubkey (base58).
        method: HTTP method (GET, POST, etc.).
        path: Request path including query string (e.g. ``/api/v1/orders``).
        body: Request body string (for POST/PUT/DELETE), omit for GET.

    Returns:
        Dict of ``HEX-*`` headers to include in the request.
    """
    timestamp = int(time.time())
    payload = build_l2_signing_payload(timestamp, method, path, body)
    signature = sign_l2(creds.secret, payload)

    return {
        "HEX-ADDRESS": pubkey,
        "HEX-API-KEY": creds.api_key,
        "HEX-PASSPHRASE": creds.passphrase,
        "HEX-TIMESTAMP": str(timestamp),
        "HEX-SIGNATURE": signature,
    }


# ---------------------------------------------------------------------------
# L1 wallet auth token
# ---------------------------------------------------------------------------

AUTH_MESSAGE_PREFIX = "hexmarket:auth\n"


def build_auth_message(timestamp: int) -> bytes:
    """Build the auth message bytes: ``hexmarket:auth\\n{timestamp}``."""
    return f"{AUTH_MESSAGE_PREFIX}{timestamp}".encode()


def build_auth_token(pubkey: str, timestamp: int, signature_b58: str) -> str:
    """Build a signed auth token: ``{pubkey}.{timestamp}.{signature_b58}``."""
    return f"{pubkey}.{timestamp}.{signature_b58}"


# ---------------------------------------------------------------------------
# Order message signing
# ---------------------------------------------------------------------------


def build_order_message(
    outcome_id: str,
    side: str,
    price: str,
    quantity: int,
    nonce: int,
) -> bytes:
    """Build the canonical order message for wallet signing.

    Must match the server-side ``build_order_message`` exactly.
    """
    msg = "\n".join([
        "hexmarket:place_order",
        f"outcome_id:{outcome_id}",
        f"side:{side}",
        f"price:{price}",
        f"quantity:{quantity}",
        f"nonce:{nonce}",
    ])
    return msg.encode()


def build_api_key_message(nonce: int) -> bytes:
    """Build the message for API key creation: ``hexmarket:create_api_key\\n{nonce}``."""
    return f"hexmarket:create_api_key\n{nonce}".encode()


def generate_nonce() -> int:
    """Generate a nonce for replay protection.

    Uses timestamp in ms * 1000 + random suffix.
    """
    return int(time.time() * 1000) * 1000 + random.randint(0, 999)


# ---------------------------------------------------------------------------
# Ed25519 signing helpers
# ---------------------------------------------------------------------------


def ed25519_sign(secret_key_bytes: bytes, message: bytes) -> str:
    """Sign a message with an Ed25519 secret key, returning base58-encoded signature.

    Args:
        secret_key_bytes: 32-byte Ed25519 secret key (seed).
        message: Message bytes to sign.

    Returns:
        Base58-encoded signature string.
    """
    import base58

    signing_key = SigningKey(secret_key_bytes)
    signed = signing_key.sign(message)
    return base58.b58encode(signed.signature).decode()


def pubkey_b58(secret_key_bytes: bytes) -> str:
    """Get the base58-encoded public key from an Ed25519 secret key.

    Args:
        secret_key_bytes: 32-byte Ed25519 secret key (seed).

    Returns:
        Base58-encoded public key string.
    """
    import base58

    signing_key = SigningKey(secret_key_bytes)
    return base58.b58encode(bytes(signing_key.verify_key)).decode()
