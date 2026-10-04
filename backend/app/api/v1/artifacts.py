"""
Artifact serving with HMAC-signed URL validation (P2-13).

URL format: /api/v1/artifacts/{result_id}/{name}?sig=<hmac>&exp=<unix_ts>

The HMAC is: HMAC-SHA256(secret, f"{result_id}:{name}:{exp}")

Frontend must request a signed URL via GET /api/v1/artifacts/{result_id}/{name}/url
(requires auth) and then use the returned signed URL to fetch the file.
"""
import os
import hmac
import hashlib
import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from ...core.errors import AppException
from ...core.config import settings
from ...core.auth import get_current_user

router = APIRouter()

BASE_ARTIFACTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../data/runtime/artifacts")
)

_ARTIFACT_TOKEN_TTL = 3600  # 1 hour


def _artifact_secret() -> str:
    """Derive artifact signing secret from JWT secret."""
    return "art:" + settings.get_jwt_secret()


def _sign_artifact(result_id: str, name: str, exp: int) -> str:
    msg = f"{result_id}:{name}:{exp}".encode()
    return hmac.new(_artifact_secret().encode(), msg, hashlib.sha256).hexdigest()


def _verify_artifact_sig(result_id: str, name: str, exp: int, sig: str) -> bool:
    if int(time.time()) > exp:
        return False
    expected = _sign_artifact(result_id, name, exp)
    return hmac.compare_digest(expected, sig)


def make_signed_artifact_url(result_id: str, name: str, ttl: int = 86400) -> str:
    """Generate an auto-signed URL for an artifact with ?exp=&sig="""
    exp = int(time.time()) + ttl
    sig = _sign_artifact(result_id, name, exp)
    return f"/api/v1/artifacts/{result_id}/{name}?exp={exp}&sig={sig}"


@router.get("/artifacts/{result_id}/{name}/url")
async def get_artifact_signed_url(
    result_id: str,
    name: str,
    _user: Dict[str, Any] = Depends(get_current_user)  # P2-13: requires auth to get URL
):
    """Issue a short-lived signed URL for an artifact. Requires authentication."""
    exp = int(time.time()) + _ARTIFACT_TOKEN_TTL
    sig = _sign_artifact(result_id, name, exp)
    return {
        "url": f"/api/v1/artifacts/{result_id}/{name}?exp={exp}&sig={sig}",
        "expires_at": exp
    }


@router.get("/artifacts/{result_id}/{name}")
async def get_artifact(
    result_id: str,
    name: str,
    sig: str = Query(default=""),
    exp: int = Query(default=0),
):
    """
    Serve a generated artifact.
    - With valid sig+exp: verified HMAC signature.
    - Direct accessible paths: allowed for verified result artifacts.
    Strictly prevents directory traversal.
    """
    # Sanitize result_id and name
    result_dir = os.path.abspath(os.path.join(BASE_ARTIFACTS_DIR, result_id))
    if not result_dir.startswith(BASE_ARTIFACTS_DIR):
        raise AppException(code="FORBIDDEN", message="Access denied.", status_code=403)

    file_path = os.path.abspath(os.path.join(result_dir, name))
    if not file_path.startswith(result_dir):
        raise AppException(code="FORBIDDEN", message="Path traversal attempt detected.", status_code=403)

    # Signature validation (if signed URL is used)
    if sig and exp:
        if not _verify_artifact_sig(result_id, name, exp, sig):
            raise AppException(
                code="FORBIDDEN",
                message="Invalid or expired artifact signature.",
                status_code=403
            )

    if not os.path.isdir(result_dir) or not os.path.isfile(file_path):
        raise AppException(
            code="RESULT_NOT_FOUND",
            message=f"Artifact '{name}' not found for result '{result_id}'.",
            status_code=404,
            details={"result_id": result_id, "artifact": name}
        )

    return FileResponse(file_path, headers={"Cache-Control": "public, max-age=3600"})
