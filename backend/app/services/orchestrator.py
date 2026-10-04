import asyncio
import uuid
import datetime
import os
import json
import logging
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path

from . import job_manager
from ..scoring.fusion import compute_fusion_with_contributions
from ..scoring.bands import get_band, determine_confidence
from ..scoring.overall import compute_overall_score
from ..scoring.overrides import apply_overrides_with_entries
from ..explain.explainer import format_summary
from ..schemas.result import (
    AnalysisResult,
    OverallScore,
    PipelineScore,
    DetectorStatus,
    QualityWarning,
    WhyThisScore,
    WhyThisScoreItem,
    QualityGateApplied,
    PipelineWhy,
    OverallWhy,
    CheckRunItem,
    PageInfo,
    LivenessStatus,
    AadhaarQrStatus,
    QrComparison,
    ChallengeStatus,
    VoiceDetails,
)
from ..schemas.evidence import Evidence
from ..detectors.base import AnalysisContext
from ..pipelines import image_pipeline, document_pipeline, claim_pipeline, identity_pipeline, voice_pipeline
from ..scoring.weights import EVIDENCE_CATALOG
from ..core.config import settings
from ..db import repository

logger = logging.getLogger("lucen_ai.orchestrator")

# In-memory fast cache
RESULTS_DB: Dict[str, AnalysisResult] = {}

BASE_ARTIFACTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/runtime/artifacts")
)

def _artifact_url(res_id: str, filename: str) -> str:
    try:
        from ..api.v1.artifacts import make_signed_artifact_url
        return make_signed_artifact_url(res_id, filename)
    except Exception:
        return f"/api/v1/artifacts/{res_id}/{filename}"

def _normalize_heatmap_artifact(artifacts: Dict[str, Any]) -> None:
    if not isinstance(artifacts, dict):
        return
    hm = artifacts.get("heatmap")
    real_hm = (
        artifacts.get("image_heatmap")
        or artifacts.get("overlay")
        or artifacts.get("ela_heatmap")
    )
    if real_hm and (not hm or str(hm).split("?")[0].lower().endswith(".json")):
        artifacts["heatmap"] = real_hm

def get_result(result_id: str) -> Optional[AnalysisResult]:
    if result_id in RESULTS_DB:
        res = RESULTS_DB[result_id]
        if res.artifacts:
            _normalize_heatmap_artifact(res.artifacts)
        return res

    try:
        row = repository.get_result(result_id)
        if row and row.get("json"):
            data = json.loads(row["json"])
            if isinstance(data.get("artifacts"), dict):
                _normalize_heatmap_artifact(data["artifacts"])
            res = AnalysisResult(**data)
            RESULTS_DB[result_id] = res
            return res
    except Exception:
        pass
    return None

def _build_pipeline_why(
    ev_list: List[Evidence],
    risk: float,
    overrides: List[str],
    quality_warnings: List[QualityWarning]
) -> PipelineWhy:
    contrib_items: List[WhyThisScoreItem] = []
    terms_str = []
    for e in ev_list:
        if e.kind != "risk":
            continue
        w = float(e.effective_weight if e.effective_weight is not None else (e.weight or 0.0))
        p = float(e.calibrated_score if e.calibrated_score is not None else 0.0)
        push = round(w * p, 4)
        contrib = float(e.contribution or 0.0)
        contrib_pct = round((contrib / risk * 100.0), 1) if risk > 0 else 0.0
        contrib_items.append(WhyThisScoreItem(
            evidence_id=e.id,
            title=e.title or e.id,
            w=w,
            p=p,
            push=push,
            contribution_pct=contrib_pct
        ))
        if push >= 0.02 and p >= 0.2:
            terms_str.append(f"(1 - {push:.3f})")

    if terms_str:
        formula_str = f"1 - {' * '.join(terms_str)} = {risk:.3f}"
    else:
        formula_str = f"No participating risk signals = {risk:.3f}"

    qg_list = []
    for qw in quality_warnings:
        qg_list.append(QualityGateApplied(
            detector=getattr(qw, "code", "QUALITY"),
            factor=0.7,
            reason=getattr(qw, "message", "Quality attenuation applied")
        ))

    return PipelineWhy(
        evidence_contributions=contrib_items,
        formula=formula_str,
        overrides_applied=overrides,
        quality_gates_applied=qg_list
    )

def _build_overall_why(
    pipeline_risks: Dict[str, float],
    overall_risk: float,
    overrides: List[str]
) -> OverallWhy:
    if not pipeline_risks:
        formula_str = "No active pipelines = 0.000"
    elif len(pipeline_risks) == 1:
        pipe_name = next(iter(pipeline_risks.keys()))
        formula_str = f"Single active pipeline ({pipe_name}) = {overall_risk:.3f}"
    else:
        vals = list(pipeline_risks.values())
        max_v = max(vals)
        mean_v = sum(vals) / len(vals)
        formula_str = (
            f"0.7 * max({max_v:.3f}) + 0.3 * mean({mean_v:.3f}) = "
            f"0.7*{max_v:.3f} + 0.3*{mean_v:.3f} = {overall_risk:.3f}"
        )

    return OverallWhy(
        formula=formula_str,
        pipeline_risks=pipeline_risks,
        overrides_applied=overrides
    )

def _build_qr_comparisons(qr_data: Dict[str, Any]) -> List[QrComparison]:
    """Builds typed printed-vs-QR comparisons from the detector's flat dict
    (keys printed_<field> / qr_<field>); match = field not listed in mismatches."""
    comps_raw = qr_data.get("comparisons") or {}
    mismatch_fields = {
        str(m.get("field")) for m in (qr_data.get("mismatches") or []) if isinstance(m, dict)
    }
    out: List[QrComparison] = []
    for field_name in ("name", "dob", "gender"):
        printed = comps_raw.get(f"printed_{field_name}")
        qr_val = comps_raw.get(f"qr_{field_name}")
        if printed is None and qr_val is None:
            continue
        out.append(QrComparison(
            field=field_name,
            printed=str(printed or ""),
            qr=str(qr_val or ""),
            match=field_name not in mismatch_fields,
        ))
    return out


def _standalone_duplicate_evidence(img_path: str, slot: str) -> List[Evidence]:
    """Duplicate search for single-image analyses (claim mode uses claim_pipeline).
    Standalone analyses are indexed under claimant 'standalone' with a unique slot per
    analysis, so a repeat upload is reported as IMG-DUP-01 (same submitter, other analysis)."""
    from ..detectors.image.duplicates import search_duplicates
    out: List[Evidence] = []
    matches = search_duplicates(
        image_path=img_path, current_claim_id=None,
        current_claimant_id="standalone", current_slot=slot,
    )
    if not matches:
        return out
    best = matches[0]
    diff = best.get("different_claimant", False)
    ev_id = "IMG-DUP-02" if diff else "IMG-DUP-01"
    cat = EVIDENCE_CATALOG[ev_id]
    sim = float(best["similarity"])
    other = best.get("other_claim_id") or "an earlier analysis"
    out.append(Evidence(
        id=ev_id, pipeline="image", source="duplicates", kind="risk",
        raw_score=round(sim, 3), calibrated_score=round(sim, 3),
        weight=cat["weight"], effective_weight=cat["weight"], severity="high",
        title=cat["title"],
        reason=f"This photo closely matches one analysed earlier ({other}, {int(sim * 100)}% similar, {best.get('match_type', 'exact')}).",
        details={"other_claim_id": other, "similarity": sim,
                 "match_type": best.get("match_type", "exact"),
                 "different_claimant": diff,
                 "thumbnail_earlier": best.get("thumbnail_earlier")},
    ))
    return out


async def _execute_analysis_job(job_id: str, mode: str, file_paths: Optional[Any] = None):
    res_id = str(uuid.uuid4())
    result_artifacts_dir = os.path.join(BASE_ARTIFACTS_DIR, res_id)
    os.makedirs(result_artifacts_dir, exist_ok=True)

    try:
        # 1. Input normalization
        images_list: List[str] = []
        document_path: Optional[str] = None
        id_photo_path: Optional[str] = None
        selfie_path: Optional[str] = None
        voice_audio_path: Optional[str] = None
        liveness_session_id: Optional[str] = None

        extra_documents: List[str] = []

        if isinstance(file_paths, dict):
            images_list = file_paths.get("images", [])
            document_path = file_paths.get("document")
            extra_documents = file_paths.get("extra_documents", [])
            id_photo_path = file_paths.get("id_photo")
            selfie_path = file_paths.get("selfie")
            voice_audio_path = file_paths.get("voice_audio") or file_paths.get("voice") or file_paths.get("audio")
            meta = file_paths.get("metadata") or {}
            
            debug_log = True
            if debug_log:
                print(f"ORCHESTRATOR LOG for {res_id} (claim mode):", flush=True)
                print(f"images_list count: {len(images_list)}", flush=True)
                print(f"document present?: {document_path is not None}", flush=True)
                print(f"id_photo present?: {id_photo_path is not None}", flush=True)
                print(f"selfie present?: {selfie_path is not None}", flush=True)
                print(f"voice present?: {voice_audio_path is not None}", flush=True)
            
            if isinstance(meta, dict):
                liveness_session_id = meta.get("liveness_session_id")
                if not voice_audio_path:
                    voice_audio_path = meta.get("voice_audio")
            if not liveness_session_id:
                liveness_session_id = file_paths.get("liveness_session_id")
        elif isinstance(file_paths, list):
            meta = {}
            if mode == "image":
                images_list = file_paths
            elif mode == "document":
                document_path = file_paths[0] if file_paths else None
            elif mode == "claim":
                images_list = file_paths
            elif mode == "identity":
                if len(file_paths) > 0:
                    id_photo_path = file_paths[0]
                if len(file_paths) > 1:
                    selfie_path = file_paths[1]
            elif mode == "voice":
                voice_audio_path = file_paths[0] if file_paths else None
        elif isinstance(file_paths, str):
            meta = {}
            if mode == "image":
                images_list = [file_paths]
            elif mode == "document":
                document_path = file_paths
            elif mode == "identity":
                id_photo_path = file_paths
            elif mode == "voice":
                voice_audio_path = file_paths
        else:
            meta = {}

        all_evidence: List[Evidence] = []
        all_statuses: List[DetectorStatus] = []
        all_quality_warnings: List[QualityWarning] = []
        result_artifacts: Dict[str, Any] = {}
        pipeline_risks_dict: Dict[str, float] = {}

        image_results: List[PipelineScore] = []
        img_score: Optional[PipelineScore] = None
        doc_score: Optional[PipelineScore] = None
        id_score: Optional[PipelineScore] = None
        voice_score: Optional[PipelineScore] = None
        claim_score: Optional[PipelineScore] = None
        image_why: Optional[PipelineWhy] = None
        doc_why: Optional[PipelineWhy] = None
        id_why: Optional[PipelineWhy] = None
        voice_why: Optional[PipelineWhy] = None
        claim_why: Optional[PipelineWhy] = None
        location_obj: Optional[Dict[str, Any]] = None
        collected_images_data: List[Dict[str, Any]] = []
        collected_doc_fields: Dict[str, Any] = {}
        collected_id_info: Dict[str, Any] = {}
        collected_voice_fields: Dict[str, Any] = {}
        liveness_status_obj: Optional[LivenessStatus] = None
        aadhaar_qr_status_obj: Optional[AadhaarQrStatus] = None
        story_status_obj: Optional[StoryStatus] = None
        has_disagreement = False

        # Copy upload previews
        for idx, img_p in enumerate(images_list):
            preview_filename = f"preview_img_{idx + 1}.jpg"
            preview_dest = os.path.join(result_artifacts_dir, preview_filename)
            try:
                shutil.copyfile(img_p, preview_dest)
                result_artifacts[f"preview_img_{idx + 1}"] = _artifact_url(res_id, preview_filename)
                if idx == 0:
                    result_artifacts["preview_image"] = result_artifacts[f"preview_img_{idx + 1}"]
            except Exception:
                pass

        if document_path:
            ext = Path(document_path).suffix or ".pdf"
            preview_filename = f"preview_doc{ext}"
            preview_dest = os.path.join(result_artifacts_dir, preview_filename)
            try:
                shutil.copyfile(document_path, preview_dest)
                result_artifacts["preview_document"] = _artifact_url(res_id, preview_filename)
            except Exception:
                pass

        if id_photo_path:
            ext = Path(id_photo_path).suffix or ".jpg"
            preview_filename = f"preview_id{ext}"
            preview_dest = os.path.join(result_artifacts_dir, preview_filename)
            try:
                shutil.copyfile(id_photo_path, preview_dest)
                result_artifacts["preview_id_photo"] = _artifact_url(res_id, preview_filename)
            except Exception:
                pass

        if selfie_path:
            ext = Path(selfie_path).suffix or ".jpg"
            preview_filename = f"preview_selfie{ext}"
            preview_dest = os.path.join(result_artifacts_dir, preview_filename)
            try:
                shutil.copyfile(selfie_path, preview_dest)
                result_artifacts["preview_selfie"] = _artifact_url(res_id, preview_filename)
            except Exception:
                pass

        if voice_audio_path:
            ext = Path(voice_audio_path).suffix or ".wav"
            preview_filename = f"preview_voice{ext}"
            preview_dest = os.path.join(result_artifacts_dir, preview_filename)
            try:
                shutil.copyfile(voice_audio_path, preview_dest)
                result_artifacts["preview_voice"] = _artifact_url(res_id, preview_filename)
            except Exception:
                pass

        # 2. Parallel Pipeline Dispatch
        tasks = []
        task_meta = []

        # Image pipelines
        for idx, img_p in enumerate(images_list):
            pfx = f"img_{idx + 1}:" if (mode == "claim" or len(images_list) > 1) else ""
            ctx_i = AnalysisContext(job_id=job_id, file_paths=[img_p], mode="image")
            ctx_i.scratch["artifacts_dir"] = result_artifacts_dir
            tasks.append(image_pipeline.run_image_pipeline(ctx_i, prefix=pfx))
            task_meta.append(("image", idx, pfx, ctx_i))

        # Document pipeline
        if document_path or mode == "document":
            pfx = "doc:" if mode == "claim" else ""
            doc_files = [document_path] if document_path else []
            ctx_d = AnalysisContext(job_id=job_id, file_paths=doc_files, mode="document")
            ctx_d.scratch["artifacts_dir"] = result_artifacts_dir
            tasks.append(document_pipeline.run_document_pipeline(ctx_d, prefix=pfx))
            task_meta.append(("document", 0, pfx, ctx_d))

        # Identity pipeline
        if id_photo_path or selfie_path or mode == "identity" or (mode == "claim" and (id_photo_path or selfie_path or liveness_session_id)):
            pfx = "id:" if mode == "claim" else ""
            id_files = [p for p in [id_photo_path, selfie_path] if p]
            ctx_id = AnalysisContext(job_id=job_id, file_paths=id_files, mode="identity")
            ctx_id.scratch["id_photo_path"] = id_photo_path
            ctx_id.scratch["selfie_path"] = selfie_path
            ctx_id.scratch["liveness_session_id"] = liveness_session_id
            ctx_id.scratch["artifacts_dir"] = result_artifacts_dir
            tasks.append(identity_pipeline.run_identity_pipeline(ctx_id, prefix=pfx))
            task_meta.append(("identity", 0, pfx, ctx_id))

        # Voice pipeline
        if voice_audio_path or mode == "voice":
            pfx = "voice:" if mode == "claim" else ""
            voice_files = [voice_audio_path] if voice_audio_path else []
            ctx_v = AnalysisContext(job_id=job_id, file_paths=voice_files, mode="voice")
            ctx_v.scratch["claim_metadata"] = meta
            ctx_v.scratch["artifacts_dir"] = result_artifacts_dir
            tasks.append(voice_pipeline.run_voice_pipeline(ctx_v))
            task_meta.append(("voice", 0, pfx, ctx_v))

        # Execute concurrent tasks
        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        pages_metadata: List[PageInfo] = []

        # 3. Process outputs
        for (task_type, idx, pfx, task_ctx), out in zip(task_meta, outputs):
            if isinstance(out, Exception):
                logger.error(f"Task {task_type} failed with error: {out}")
                all_statuses.append(DetectorStatus(
                    detector=f"{pfx}{task_type}",
                    status="failed",
                    duration_ms=0,
                    error=str(out)
                ))
                continue

            if task_type == "image":
                img_out = out
                all_statuses.extend(img_out.status)
                input_tag = f"img_{idx + 1}" if (mode == "claim" or len(images_list) > 1) else "image"
                collected_images_data.append({
                    "slot": input_tag,
                    "path": images_list[idx] if idx < len(images_list) else None,
                    "exif_summary": img_out.extras.get("exif_summary", {})
                })

                ev = img_out.evidence or []
                ev_dicts = [e.model_dump() for e in ev]
                risk, contribs = compute_fusion_with_contributions(ev_dicts)

                input_tag = f"img_{idx + 1}" if (mode == "claim" or len(images_list) > 1) else "image"
                for e in ev:
                    e.pipeline_input = input_tag
                    e.page = 1
                    c = contribs.get(e.id, 0.0)
                    e.contribution = c
                    e.contribution_pct = round((c / risk * 100.0), 1) if risk > 0 else 0.0
                    e.details = e.details or {}
                    e.details["contribution"] = c

                risk, applied_img_overrides = apply_overrides_with_entries([e.id for e in ev], risk, "image")
                score_item = PipelineScore(
                    pipeline=input_tag,
                    risk=risk,
                    authenticity=round(1.0 - risk, 4),
                    band=get_band(risk),
                    confidence="high",
                    evidence_ids=[e.id for e in ev]
                )
                image_results.append(score_item)
                all_evidence.extend(ev)

                for art_name, art_path in img_out.artifacts.items():
                    result_artifacts[art_name] = _artifact_url(res_id, Path(art_path).name)

                qw = img_out.extras.get("quality_warnings", [])
                if qw:
                    all_quality_warnings.extend(qw)

                if img_out.extras.get("tta_disagreement"):
                    has_disagreement = True

                # Generate why for this image
                if image_why is None or (score_item.risk >= (img_score.risk if img_score else -1)):
                    image_why = _build_pipeline_why(
                        ev,
                        risk,
                        [r["text"] for r in applied_img_overrides],
                        qw
                    )

            elif task_type == "document":
                doc_out = out
                all_statuses.extend(doc_out.status)
                for i, extra_doc in enumerate(extra_documents):
                    all_statuses.append(DetectorStatus(
                        detector=f"extra_document_{i+1}",
                        status="skipped",
                        duration_ms=0,
                        error="additional document"
                    ))

                ev = doc_out.evidence or []

                # P0-5: CNN corroboration cap lift — check if DOC-CNN-01 bbox
                # overlaps any rule-based flag (DOC-LOGIC-*, DOC-FONT-*, DOC-OVERLAY-01).
                # If so, add "forensics" to corroborated_sources to lift the source cap to 1.0.
                _cnn_corroborated: set = set()
                _cnn_evs = [e for e in ev if e.id == "DOC-CNN-01" and e.bbox]
                _rule_evs = [
                    e for e in ev
                    if (e.id.startswith("DOC-LOGIC-") or e.id.startswith("DOC-FONT-")
                        or e.id == "DOC-OVERLAY-01") and e.bbox
                ]
                for _cnn_ev in _cnn_evs:
                    cb = _cnn_ev.bbox
                    for _r_ev in _rule_evs:
                        rb = _r_ev.bbox
                        if rb.page == cb.page:
                            # IoU-style overlap: check if rectangles intersect
                            _x_overlap = max(0.0, min(cb.x + cb.w, rb.x + rb.w) - max(cb.x, rb.x))
                            _y_overlap = max(0.0, min(cb.y + cb.h, rb.y + rb.h) - max(cb.y, rb.y))
                            if _x_overlap > 0 and _y_overlap > 0:
                                _cnn_corroborated.add("forensics")
                                logger.debug(
                                    f"DOC-CNN-01 bbox overlaps {_r_ev.id} on page {rb.page}; "
                                    "lifting forensics cap to 1.0"
                                )
                                break

                # When uncorroborated, mark DOC-CNN-01 as kind='warning' with specific reason
                if "forensics" not in _cnn_corroborated:
                    for e in ev:
                        if e.id == "DOC-CNN-01":
                            e.kind = "warning"
                            e.reason = "Unconfirmed compression pattern – no supporting field evidence"
                            if e.details is None:
                                e.details = {}
                            e.details["corroborated"] = False
                else:
                    for e in ev:
                        if e.id == "DOC-CNN-01":
                            if e.details is None:
                                e.details = {}
                            e.details["corroborated"] = True

                ev_dicts = [e.model_dump() for e in ev]
                risk, contribs = compute_fusion_with_contributions(ev_dicts, corroborated_sources=_cnn_corroborated)

                for e in ev:
                    e.pipeline_input = "doc"
                    c = contribs.get(e.id, 0.0)
                    e.contribution = c
                    e.contribution_pct = round((c / risk * 100.0), 1) if risk > 0 else 0.0
                    e.details = e.details or {}
                    e.details["contribution"] = c

                risk, applied_doc_overrides = apply_overrides_with_entries([e.id for e in ev], risk, "document")
                doc_conf = "low" if (doc_out.status and all(s.status in ("skipped", "failed") for s in doc_out.status)) else "high"
                doc_score = PipelineScore(
                    pipeline="document",
                    risk=risk,
                    authenticity=round(1.0 - risk, 4),
                    band=get_band(risk),
                    confidence=doc_conf,
                    evidence_ids=[e.id for e in ev]
                )
                pipeline_risks_dict["document"] = risk
                all_evidence.extend(ev)

                for art_name, art_path in doc_out.artifacts.items():
                    result_artifacts[art_name] = _artifact_url(res_id, Path(art_path).name)

                if "document_pages" in doc_out.extras:
                    for dp in doc_out.extras["document_pages"]:
                        p_info = PageInfo(
                            page=dp["page"],
                            width_pt=595.0,
                            height_pt=842.0,
                            image_url=_artifact_url(res_id, dp["image"]),
                            annotated_url=_artifact_url(res_id, dp["annotated_boxes"]),
                            tamper_heatmap_url=_artifact_url(res_id, dp["tamper_heatmap"]) if dp.get("tamper_heatmap") else None
                        )
                        pages_metadata.append(p_info)

                qw = doc_out.extras.get("quality_warnings", [])
                if qw:
                    all_quality_warnings.extend(qw)

                doc_why = _build_pipeline_why(
                    ev,
                    risk,
                    [r["text"] for r in applied_doc_overrides],
                    qw
                )
                collected_doc_fields = doc_out.extras.get("extracted_fields", {})

            elif task_type == "identity":
                id_out = out
                collected_id_info = id_out.extras
                all_statuses.extend(id_out.status)
                if id_out.evidence:
                    for e in id_out.evidence:
                        if not e.pipeline_input:
                            e.pipeline_input = "identity"
                    all_evidence.extend(id_out.evidence)

                for art_name, art_path in id_out.artifacts.items():
                    result_artifacts[art_name] = _artifact_url(res_id, Path(art_path).name)

                id_risk_ev = [e for e in id_out.evidence if e.kind == "risk"]
                if id_risk_ev:
                    id_ev_dicts = [e.model_dump() for e in id_risk_ev]
                    id_risk, id_contribs = compute_fusion_with_contributions(id_ev_dicts)
                    for e in id_out.evidence:
                        c = id_contribs.get(e.id, 0.0)
                        e.contribution = c
                        e.contribution_pct = round((c / id_risk * 100.0), 1) if id_risk > 0 else 0.0
                        e.details = e.details or {}
                        e.details["contribution"] = c
                else:
                    id_risk = 0.05

                id_risk, applied_id_overrides = apply_overrides_with_entries(
                    [e.id for e in id_out.evidence],
                    id_risk,
                    "identity"
                )

                id_band = get_band(id_risk)
                id_score = PipelineScore(
                    pipeline="identity",
                    risk=round(id_risk, 4),
                    authenticity=round(1.0 - id_risk, 4),
                    band=id_band,
                    confidence="high",
                    evidence_ids=[e.id for e in id_out.evidence]
                )
                pipeline_risks_dict["identity"] = id_score.risk

                id_why = _build_pipeline_why(
                    id_out.evidence,
                    id_risk,
                    [r["text"] for r in applied_id_overrides],
                    []
                )

                liv_data = id_out.extras.get("liveness", {})
                if liv_data:
                    liveness_status_obj = LivenessStatus(
                        performed=liv_data.get("status") in ("passed", "failed"),
                        passed=liv_data.get("status") == "passed",
                        code_match=True,
                        challenges=[]
                    )

                qr_data = id_out.extras.get("aadhaar_qr", {})
                if qr_data and qr_data.get("has_qr"):
                    comps = _build_qr_comparisons(qr_data)
                    photo_sim = id_out.extras.get("face", {}).get("similarity")
                    photo_sim_val = float(photo_sim) if photo_sim is not None else 0.0
                    aadhaar_qr_status_obj = AadhaarQrStatus(
                        found=True,
                        signature_valid=bool(qr_data.get("signature_valid")),
                        mode=str(qr_data.get("key_label", "production")),
                        comparisons=comps,
                        photo_similarity=round(photo_sim_val, 4)
                    )

            elif task_type == "voice":
                voice_out = out
                all_statuses.extend(voice_out.status)
                ev = voice_out.evidence or []
                for e in ev:
                    if not e.pipeline_input:
                        e.pipeline_input = "voice"
                all_evidence.extend(ev)

                for art_name, art_path in voice_out.artifacts.items():
                    result_artifacts[art_name] = _artifact_url(res_id, Path(art_path).name)

                qw = [e for e in ev if e.kind == "warning" and e.id == "VOI-QUAL-01"]
                for w in qw:
                    all_quality_warnings.append(QualityWarning(code=w.id, message=w.reason))

                voice_risk_ev = [e for e in ev if e.kind == "risk"]
                if voice_risk_ev:
                    voice_ev_dicts = [e.model_dump() for e in voice_risk_ev]
                    voice_risk, voice_contribs = compute_fusion_with_contributions(voice_ev_dicts)
                    for e in ev:
                        c = voice_contribs.get(e.id, 0.0)
                        e.contribution = c
                        e.contribution_pct = round((c / voice_risk * 100.0), 1) if voice_risk > 0 else 0.0
                        e.details = e.details or {}
                        e.details["contribution"] = c
                else:
                    voice_risk = 0.0

                voice_score = PipelineScore(
                    pipeline="voice",
                    risk=round(voice_risk, 4),
                    authenticity=round(1.0 - voice_risk, 4),
                    band=get_band(voice_risk),
                    confidence="high",
                    evidence_ids=[e.id for e in ev]
                )
                pipeline_risks_dict["voice"] = voice_score.risk

                voice_why = _build_pipeline_why(
                    ev,
                    voice_risk,
                    [],
                    [w for w in all_quality_warnings if "VOI" in getattr(w, "code", "")]
                )
                collected_voice_fields = voice_out.extras.get("extracted_fields", {})
                voice_details_dict = {
                    "language": voice_out.extras.get("language"),
                    "transcript": voice_out.extras.get("transcript"),
                    "translation_en": voice_out.extras.get("translation_en"),
                    "extracted": collected_voice_fields,
                    "spoof": voice_out.extras.get("spoof_evidence")
                }

        # 4. Top-level image score selection (§15.5)
        if image_results:
            top_img = max(image_results, key=lambda s: s.risk)
            img_score = PipelineScore(
                pipeline="image",
                risk=top_img.risk,
                authenticity=top_img.authenticity,
                band=top_img.band,
                confidence=top_img.confidence,
                evidence_ids=top_img.evidence_ids
            )
            pipeline_risks_dict["image"] = img_score.risk

        # 5. Claim Pipeline Cross-Checks (§14, Prompt 8)
        if mode == "claim":
            claim_ctx = AnalysisContext(job_id=job_id, file_paths=[], mode="claim")
            claim_ctx.scratch["claim_metadata"] = meta
            cid = meta.get("claim_id") or (file_paths.get("claim_id") if isinstance(file_paths, dict) else None)
            uid = meta.get("claimant_user_id") or (file_paths.get("claimant_id") if isinstance(file_paths, dict) else None)
            claim_ctx.scratch["claim_id"] = cid
            claim_ctx.scratch["claimant_id"] = uid
            claim_ctx.scratch["images_data"] = collected_images_data
            claim_ctx.scratch["document_fields"] = collected_doc_fields
            claim_ctx.scratch["identity_info"] = collected_id_info
            claim_ctx.scratch["voice_fields"] = collected_voice_fields

            c_ev, c_statuses, r_claim, c_extras = await claim_pipeline.run_claim_pipeline(claim_ctx)
            all_statuses.extend(c_statuses)
            location_obj = c_extras.get("location")
            if location_obj:
                result_artifacts["location"] = location_obj
            if c_extras.get("story"):
                story_status_obj = c_extras.get("story")
            if c_ev:
                all_evidence.extend(c_ev)

            r_claim, applied_claim_overrides = apply_overrides_with_entries([e.id for e in c_ev], r_claim, "claim")
            claim_score = PipelineScore(
                pipeline="claim",
                risk=round(r_claim, 4),
                authenticity=round(1.0 - r_claim, 4),
                band=get_band(r_claim),
                confidence="high",
                evidence_ids=[e.id for e in c_ev]
            )
            pipeline_risks_dict["claim"] = claim_score.risk
            claim_why = _build_pipeline_why(
                c_ev,
                r_claim,
                [r["text"] for r in applied_claim_overrides],
                []
            )

        # 6. Overall risk blend (§15.5: 0.7 * max + 0.3 * mean)
        pipeline_risks = list(pipeline_risks_dict.values())
        overall_risk = compute_overall_score(pipeline_risks)

        all_ids = [e.id for e in all_evidence]
        overall_risk, applied_overall_overrides = apply_overrides_with_entries(all_ids, overall_risk, "overall")

        for rule in applied_overall_overrides:
            all_evidence.append(
                Evidence(
                    id=f"OVERRIDE-{rule['rule']}",
                    kind="info",
                    raw_score=rule["floor"],
                    calibrated_score=rule["floor"],
                    weight=0.0,
                    effective_weight=0.0,
                    severity="high",
                    title=f"Rule {rule['rule']} Applied",
                    reason=rule["text"],
                    details={"rule": rule["rule"], "floor": rule["floor"]}
                )
            )

        band = get_band(overall_risk)
        evidence_sources = [EVIDENCE_CATALOG.get(e.id, {}).get("source", "unknown") for e in all_evidence]

        if all_statuses and all(s.status in ("skipped", "failed") for s in all_statuses):
            if not any("Some checks could not run" in (w.message or "") for w in all_quality_warnings):
                all_quality_warnings.append(
                    QualityWarning(code="CHECKS_FAILED", message="Some checks could not run")
                )

        conf = determine_confidence(
            evidence_ids=all_ids,
            detector_statuses=all_statuses,
            quality_warnings=all_quality_warnings,
            sources=evidence_sources,
            disagreement=has_disagreement,
            top_detector_auc=None,
            initial_conf="high"
        )

        # 7. Sort evidence by contribution descending & assign ranks
        risk_ev = [e for e in all_evidence if e.kind == "risk"]
        risk_ev.sort(key=lambda x: (x.contribution or 0.0), reverse=True)
        for rank_idx, e in enumerate(risk_ev):
            e.rank = rank_idx + 1

        non_risk_ev = [e for e in all_evidence if e.kind != "risk"]
        sorted_evidence = risk_ev + non_risk_ev

        # 8. Explanations & Why This Score
        summary = format_summary(band, overall_risk, [e.model_dump() for e in sorted_evidence], conf)

        overall_why = _build_overall_why(
            pipeline_risks_dict,
            overall_risk,
            [r["text"] for r in applied_overall_overrides]
        )

        all_why_items = []
        for pw in (image_why, doc_why, id_why, voice_why, claim_why):
            if pw and pw.evidence_contributions:
                all_why_items.extend(pw.evidence_contributions)
        all_why_items.sort(key=lambda x: x.contribution_pct, reverse=True)

        why_this_score = WhyThisScore(
            image=image_why,
            document=doc_why,
            identity=id_why,
            voice=voice_why,
            claim=claim_why,
            overall=overall_why,
            items=all_why_items
        )

        checks_run = [
            CheckRunItem(
                detector=s.detector,
                status=s.status,
                duration_ms=s.duration_ms,
                reason=s.error if s.status != "ok" else None
            )
            for s in all_statuses
        ]

        if risk_ev:
            top_reasons = [e.reason or e.title for e in risk_ev[:5]]
        else:
            top_reasons = ["All automated forensic integrity checks passed with no indicators of manipulation."]

        if overall_risk >= 0.65:
            recommended_action = "Escalate to Special Investigation Unit (SIU) for detailed forensic document inspection and claimant interview."
        elif overall_risk >= 0.35:
            recommended_action = "Route to senior claims adjuster for manual document review and verification of original invoice."
        else:
            recommended_action = "Approve claim for automated Straight-Through Processing (STP)."

        if any(e.id == "CLM-NET-02" for e in all_evidence):
            recommended_action += " Refer for network review."

        # 9. Final Artifacts Assembly
        if pages_metadata:
            result_artifacts["pages"] = [p.model_dump() for p in pages_metadata]
        if not result_artifacts.get("heatmap"):
            existing_heatmap = (
                result_artifacts.get("image_heatmap")
                or result_artifacts.get("overlay")
                or result_artifacts.get("ela_heatmap")
            )
            if existing_heatmap:
                result_artifacts["heatmap"] = existing_heatmap
            elif not pages_metadata:
                placeholder_path = os.path.join(result_artifacts_dir, "heatmap.json")
                with open(placeholder_path, "w", encoding="utf-8") as f:
                    json.dump({"type": "heatmap", "resolution": [512, 512], "channels": 1}, f)
                result_artifacts["heatmap"] = _artifact_url(res_id, "heatmap.json")

        now_iso = datetime.datetime.utcnow().isoformat()
        cid = meta.get("claim_id") or (file_paths.get("claim_id") if isinstance(file_paths, dict) else None)
        voice_details_obj = None
        if "voice_details_dict" in locals() and voice_details_dict:
            try:
                voice_details_obj = VoiceDetails(**voice_details_dict)
            except Exception:
                voice_details_obj = None

        res = AnalysisResult(
            id=res_id,
            claim_id=cid,
            mode=mode,
            created_at=now_iso,
            overall=OverallScore(risk=overall_risk, band=band, confidence=conf, summary=summary),
            evidence=sorted_evidence,
            image=img_score,
            document=doc_score,
            identity=id_score,
            voice=voice_score,
            voice_details=voice_details_obj,
            claim=claim_score,
            location=location_obj,
            liveness=liveness_status_obj,
            aadhaar_qr=aadhaar_qr_status_obj,
            story=story_status_obj,
            detector_status=all_statuses,
            quality_warnings=all_quality_warnings,
            artifacts=result_artifacts,
            versions={
                "detector": "Ateeqq/ai-vs-human-image-detector",
                "face_engine": getattr(settings, "FACE_ENGINE", "sface"),
                "calibration_date": "2026-10-02",
                "git_commit": "e8d47bf",
                "engine": "lucen-2.0"
            },
            image_results=image_results if image_results else None,
            why_this_score=why_this_score,
            why_this_score_items=all_why_items,
            checks_run=checks_run,
            top_reasons=top_reasons,
            recommended_action=recommended_action,
            summary_source="template"
        )
        RESULTS_DB[res_id] = res

        # 10. Persist to SQLite
        try:
            repository.insert_result(
                result_id=res_id,
                job_id=job_id,
                mode=mode,
                overall_risk=overall_risk,
                overall_band=band,
                summary=summary,
                result_json=res.model_dump_json(),
                created_at=now_iso,
                image_risk=img_score.risk if img_score else None,
                document_risk=doc_score.risk if doc_score else None,
                identity_risk=id_score.risk if id_score else None
            )
            for e in sorted_evidence:
                repository.insert_evidence_row(
                    result_id=res_id,
                    evidence_id=e.id,
                    pipeline=e.pipeline_input or ("image" if e.id.startswith("IMG") else "document" if e.id.startswith("DOC") else "claim"),
                    source=e.details.get("source", "detector") if e.details else "detector",
                    kind=e.kind,
                    raw_score=e.raw_score,
                    calibrated_score=e.calibrated_score,
                    weight=e.weight,
                    effective_weight=e.effective_weight,
                    severity=e.severity,
                    title=e.title,
                    reason=e.reason,
                    field=e.field,
                    bbox_json=e.bbox.model_dump_json() if e.bbox else None,
                    details_json=json.dumps(e.details) if e.details else None,
                    artifact=e.artifact
                )
        except Exception as e:
            logger.warning(f"Failed to persist result to SQLite: {e}")

        # 11. Post-Analysis Duplicate Indexing & Entity Store (§10, §14.3)
        try:
            skip_idx = meta.get("index") is False or meta.get("data_source") == "synthetic_history"
            if skip_idx:
                pass # skip
            else:
                from backend.app.detectors.image.duplicates import index_image
                cid = meta.get("claim_id") or (file_paths.get("claim_id") if isinstance(file_paths, dict) else None)
                uid = meta.get("claimant_user_id") or (file_paths.get("claimant_id") if isinstance(file_paths, dict) else None)
                for idx, img_p in enumerate(images_list):
                    slot_name = f"img_{idx + 1}" if (mode == "claim" or len(images_list) > 1) else "image"
                    thumb_path = os.path.join(result_artifacts_dir, f"preview_img_{idx + 1}.jpg")
                    index_image(
                        image_path=img_p,
                        claim_id=cid,
                        claimant_id=uid,
                        result_id=res_id,
                        slot=slot_name,
                        thumbnail_path=thumb_path if os.path.exists(thumb_path) else None
                    )
        except Exception as e:
            logger.warning(f"Error indexing images post-analysis: {e}")

        if mode == "claim":
            try:
                from backend.app.services.entity_store import extract_and_store_entities
                cid = meta.get("claim_id") or (file_paths.get("claim_id") if isinstance(file_paths, dict) else None)
                if cid:
                    extract_and_store_entities(
                        claim_id=cid,
                        result_id=res_id,
                        claim_data=meta,
                        doc_fields=collected_doc_fields,
                        user_data={"id": uid}
                    )
                    try:
                        from backend.app.services.network import detect_fraud_rings
                        detect_fraud_rings(rebuild=True)
                    except Exception as net_err:
                        logger.warning(f"Error updating fraud network: {net_err}")
            except Exception as e:
                logger.warning(f"Error extracting entities: {e}")

        job_manager.update_job_status(job_id, "done", result_id=res_id)
        return res

    except Exception as e:
        logger.error(f"Analysis job {job_id} encountered unhandled exception: {e}", exc_info=True)
        job_manager.update_job_status(job_id, "failed", error=str(e))


def run_analysis_job(job_id: str, mode: str, file_paths: Optional[Any] = None):
    """Executes the analysis job in a worker thread OFF the main event loop."""
    semaphore = job_manager.get_semaphore()
    with semaphore:
        job_manager.update_job_status(job_id, "running")
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(asyncio.run, _execute_analysis_job(job_id, mode, file_paths)).result()
            else:
                asyncio.run(_execute_analysis_job(job_id, mode, file_paths))
        except Exception as e:
            logger.error(f"Analysis job {job_id} failed: {e}", exc_info=True)
            job_manager.update_job_status(job_id, "failed", error=str(e))
