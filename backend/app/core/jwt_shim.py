"""
Pure-python standard HS256 JWT implementation.
"""
import base64
import hmac
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

class PyJWTError(Exception):
    pass

class InvalidTokenError(PyJWTError):
    pass

class ExpiredSignatureError(InvalidTokenError):
    pass

def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64decode(data: str) -> bytes:
    pad = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + pad)

def encode(payload: Dict[str, Any], key: str, algorithm: str = "HS256") -> str:
    if algorithm != "HS256":
        raise ValueError(f"Algorithm {algorithm} not supported, only HS256")
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    
    header_b64 = _b64encode(header_json)
    payload_b64 = _b64encode(payload_json)
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    
    signature = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode(token: str, key: str, algorithms: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
    if algorithms and "HS256" not in algorithms:
        raise InvalidTokenError("HS256 not in allowed algorithms")
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Invalid token structure (expected 3 parts)")
    
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64decode(sig_b64)
    
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise InvalidTokenError("Signature verification failed")
    
    try:
        payload_bytes = _b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise InvalidTokenError(f"Invalid payload encoding: {e}")
    
    # Check expiration
    if "exp" in payload:
        if float(payload["exp"]) < time.time():
            raise ExpiredSignatureError("Token has expired")
            
    return payload
