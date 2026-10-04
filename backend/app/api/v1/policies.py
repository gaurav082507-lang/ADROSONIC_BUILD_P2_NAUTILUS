from typing import List
from fastapi import APIRouter, Depends

from backend.app.core.auth import get_current_user, require_role
from backend.app.db.repository import list_policies_for_user
from backend.app.schemas.policy import PolicyItem

router = APIRouter(tags=["Policies"])

@router.get("/policies/mine", response_model=List[PolicyItem])
async def get_my_policies(user: dict = Depends(require_role("claimant"))):
    policies = list_policies_for_user(user["id"])
    res = []
    for p in policies:
        res.append(PolicyItem(
            policy_number=p["policy_number"],
            claim_type=p.get("claim_type") or "motor",
            sum_insured=float(p.get("sum_insured") or 0.0),
            start_date=p.get("start_date") or "",
            end_date=p.get("end_date") or "",
            vehicle_or_asset=p.get("vehicle_or_asset") or "",
            details=p.get("details") or {}
        ))
    return res
