from datetime import datetime
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Path

from backend.app.core.auth import require_role
from backend.app.core.errors import AppException
from backend.app.core.decision_reasons import (
    get_template_draft,
    validate_draft_guardrails,
    extract_numbers_from_text
)
from backend.app.db.database import get_connection
from backend.app.db.repository import (
    get_result_by_id,
    add_action_record,
    update_claim_record
)
from backend.app.schemas.decision import (
    DecisionDraftRequest,
    DecisionDraftResponse,
    DecisionSubmitRequest
)

router = APIRouter(tags=["Decisions"])

def _find_claim_for_result(result_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM claims WHERE result_id = ? ORDER BY rowid DESC", (result_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

@router.post("/results/{id}/decision/draft", response_model=DecisionDraftResponse)
async def draft_decision(
    id: str = Path(..., description="Result ID"),
    req: DecisionDraftRequest = ...,
    user: dict = Depends(require_role("investigator"))
):
    result = get_result_by_id(id)
    if not result:
        raise AppException("RESULT_NOT_FOUND", f"Result {id} not found", status_code=404)
        
    claim = _find_claim_for_result(id)
    allowed_numbers = set()
    if claim:
        allowed_numbers.update(extract_numbers_from_text(claim.get("incident_date") or ""))
        allowed_numbers.update(extract_numbers_from_text(str(claim.get("claimed_amount") or "")))
        allowed_numbers.update(extract_numbers_from_text(claim.get("policy_number") or ""))

    # Base template
    action_key = req.action.lower()
    draft = get_template_draft(action_key, req.reason_category)
    
    # If investigator provided a custom note or LLM was attempted, guardrail check
    # Check guardrails on template as well
    if not validate_draft_guardrails(draft["claimant_message_en"], allowed_numbers):
        # Fall back to safest default template
        draft = get_template_draft(action_key, "other")

    return DecisionDraftResponse(
        claimant_message_en=draft["claimant_message_en"],
        claimant_message_hi=draft["claimant_message_hi"],
        next_steps=draft["next_steps"],
        slots_to_resubmit=draft["slots_to_resubmit"],
        source="template"
    )

@router.post("/results/{id}/decision")
async def submit_decision(
    id: str = Path(..., description="Result ID"),
    req: DecisionSubmitRequest = ...,
    user: dict = Depends(require_role("investigator"))
):
    result = get_result_by_id(id)
    if not result:
        raise AppException("RESULT_NOT_FOUND", f"Result {id} not found", status_code=404)
        
    claim = _find_claim_for_result(id)
    claim_id = claim["id"] if claim else None
    
    # Map action to claim status
    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "request_evidence": "needs_evidence",
        "escalate": "under_review"
    }
    new_status = status_map.get(req.action.lower(), "under_review")
    from_status = claim.get("status") if claim else "under_review"
    
    now = datetime.utcnow().isoformat()
    if claim:
        update_claim_record(claim_id, {
            "status": new_status,
            "updated_at": now
        })
        
        # If slots need replacing, update claim_evidence states
        if req.slots_to_resubmit:
            conn = get_connection()
            for s in req.slots_to_resubmit:
                conn.execute(
                    "UPDATE claim_evidence SET state = 'needs_replacing', updated_at = ? WHERE claim_id = ? AND slot = ?",
                    (now, claim_id, s)
                )
            conn.commit()
            conn.close()

    # Log action
    add_action_record({
        "claim_id": claim_id,
        "result_id": id,
        "actor": user["name"],
        "action": req.action,
        "from_status": from_status,
        "to_status": new_status,
        "reason_category": req.reason_category,
        "reason_code": req.reason_category.upper(),
        "claimant_message": req.claimant_message,
        "internal_note": req.internal_note,
        "message_source": "manual",
        "draft_edited": 1,
        "slots_to_resubmit_json": json.dumps(req.slots_to_resubmit),
        "created_at": now
    })
    
    return {
        "status": "ok",
        "claim_id": claim_id,
        "new_status": new_status,
        "action": req.action
    }
