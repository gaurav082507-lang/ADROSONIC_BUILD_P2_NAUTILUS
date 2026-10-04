from typing import Optional, Dict, Any, Literal, List, Union
from pydantic import BaseModel, model_validator

EvidenceKind = Literal["risk", "authenticity", "info"]

class BBox(BaseModel):
    page: int = 1
    x: float
    y: float
    w: float
    h: float

class Evidence(BaseModel):
    id: str
    kind: str = "risk"  # "risk" | "authenticity" | "info"
    raw_score: float = 0.50
    calibrated_score: float = 0.50
    weight: float = 0.50
    effective_weight: float = 0.50
    severity: str = "medium"  # "low" | "medium" | "high"
    title: str = ""
    reason: str = ""
    field: Optional[str] = None
    bbox: Optional[BBox] = None
    bboxes: Optional[List[Any]] = None
    details: Optional[Dict[str, Any]] = None
    artifact: Optional[str] = None
    pipeline: Optional[str] = None
    source: Optional[str] = None
    contribution: Optional[float] = None
    contribution_pct: Optional[float] = None
    rank: Optional[int] = None
    pipeline_input: Optional[str] = None
    page: Optional[int] = 1

    @model_validator(mode="before")
    @classmethod
    def populate_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If 'score' is provided, map to raw_score and calibrated_score
            score = data.get("score")
            if score is not None:
                if "raw_score" not in data:
                    data["raw_score"] = float(score)
                if "calibrated_score" not in data:
                    data["calibrated_score"] = float(score)

            # If effective_weight is omitted, default to weight
            if "effective_weight" not in data and "weight" in data:
                data["effective_weight"] = float(data["weight"])

            # If severity is omitted, compute from calibrated_score
            if "severity" not in data:
                cal = data.get("calibrated_score", 0.5)
                if cal >= 0.65:
                    data["severity"] = "high"
                elif cal >= 0.35:
                    data["severity"] = "medium"
                else:
                    data["severity"] = "low"

            # If bboxes is provided as list of [x, y, w, h], set primary bbox
            if "bboxes" in data and data["bboxes"] and "bbox" not in data:
                first_b = data["bboxes"][0]
                if isinstance(first_b, (list, tuple)) and len(first_b) == 4:
                    data["bbox"] = BBox(page=1, x=first_b[0], y=first_b[1], w=first_b[2], h=first_b[3])
                elif isinstance(first_b, BBox):
                    data["bbox"] = first_b

        return data

    @property
    def score(self) -> float:
        return self.calibrated_score
