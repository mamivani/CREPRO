"""Password hashing for local-account fallback logins (15-day plan, Day 5).

Uses stdlib PBKDF2-HMAC-SHA256 instead of adding a hashing dependency: 600,000 iterations
matches OWASP's 2023 recommendation for PBKDF2-SHA256. Stored as `salt_hex$digest_hex` so
verification needs no extra lookup.
"""

import hashlib
import hmac
import secrets

_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    salt, _, digest_hex = hashed.partition("$")
    if not digest_hex:
        return False
    expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return hmac.compare_digest(expected.hex(), digest_hex)
