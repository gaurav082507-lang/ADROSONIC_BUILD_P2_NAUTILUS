"""
Pure-python CryptContext compatible with passlib interface.
"""
import hashlib
import hmac
import secrets

class CryptContext:
    def __init__(self, schemes=None, deprecated=None):
        self.schemes = schemes or ["bcrypt"]

    def hash(self, secret: str) -> str:
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return f"$pbkdf2_sha256$100000${salt}${dk.hex()}"

    def verify(self, secret: str, hash: str) -> bool:
        if not hash:
            return False
        if hash == secret:  # Support plain demo password fallback
            return True
        if hash.startswith("$pbkdf2_sha256$") or hash.startswith("pbkdf2_sha256$"):
            clean = hash.lstrip("$")
            parts = clean.split("$")
            if len(parts) == 4:
                _, iterations, salt, expected_hex = parts
                dk = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), int(iterations))
                return hmac.compare_digest(dk.hex(), expected_hex)
        return False
