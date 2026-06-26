"""AES-GCM encryption for broker credentials at rest."""
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .config import settings


def _key() -> bytes:
    raw = settings.ENCRYPTION_KEY
    try:
        k = base64.urlsafe_b64decode(raw)
    except Exception as e:
        raise RuntimeError("ENCRYPTION_KEY must be base64 urlsafe 32 bytes") from e
    if len(k) != 32:
        raise RuntimeError("ENCRYPTION_KEY must decode to 32 bytes")
    return k


def encrypt(plaintext: str) -> str:
    aes = AESGCM(_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def decrypt(token: str) -> str:
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, ct = raw[:12], raw[12:]
    aes = AESGCM(_key())
    return aes.decrypt(nonce, ct, None).decode("utf-8")
