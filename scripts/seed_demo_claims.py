"""
Seed demo claims (idempotent).
Populates realistic claims across Ravi Kumar and Sunita Sharma with linked results,
actions, and evidence.
"""
import os
import sys
import json
import shutil
import asyncio
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import numpy as np
from PIL import Image, ImageEnhance
import piexif

from backend.app.db.database import get_connection
from backend.app.services.orchestrator import _execute_analysis_job
from backend.app.db.repository import (
    create_claim_record,
    add_claim_evidence_item,
    add_action_record,
    get_claim_record
)
from backend.app.api.v1.mock_data import get_canned_result
from backend.app.detectors.image.duplicates import index_image
from backend.app.schemas.result import (
    AnalysisResult, OverallScore, PipelineScore, DetectorStatus,
    WhyThisScore, PipelineWhy, OverallWhy, CheckRunItem
)
from backend.app.schemas.evidence import Evidence

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "data", "demo_samples")
CLAIMS_RUNTIME = os.path.join(BASE_DIR, "data", "runtime", "claims")

DEMO_CLAIMS_CONFIG = [
    {
        "id": "claim_demo_01",
        "claimant_user_id": "user_ravi",
        "claimant_name": "Ravi Kumar",
        "policy_number": "POL-MOT-8821",
        "claim_type": "motor",
        "peril": "collision",
        "incident_date": "2026-06-10",
        "incident_time": "14:30",
        "claimed_amount": 12500.0,
        "variant": "LOW",
        "status": "approved",
        "fast_track": 1,
        "photo": "02_genuine_phone_photo.jpg",
        "doc": "clean_invoice.pdf",
        "action_note": "Fast-tracked one-click approval by investigator."
    },
    {
        "id": "claim_demo_02",
        "claimant_user_id": "user_ravi",
        "claimant_name": "Ravi Kumar",
        "policy_number": "POL-MOT-8821",
        "claim_type": "motor",
        "peril": "collision",
        "incident_date": "2026-07-02",
        "incident_time": "18:45",
        "claimed_amount": 88500.0,
        "variant": "HIGH",
        "status": "under_review",
        "fast_track": 0,
        "photo": "01_ai_generated_car_damage.jpg",
        "doc": "tampered_invoice.pdf",
        "action_note": "Initial analysis completed. High risk detected."
    },
    {
        "id": "claim_demo_03",
        "claimant_user_id": "user_ravi",
        "claimant_name": "Ravi Kumar",
        "policy_number": "POL-PRP-1093",
        "claim_type": "property",
        "peril": "water_leak",
        "incident_date": "2026-07-15",
        "incident_time": "11:00",
        "claimed_amount": 35000.0,
        "variant": "MEDIUM",
        "status": "needs_evidence",
        "fast_track": 0,
        "photo": "04_low_res_compressed.jpg",
        "doc": "clean_invoice.pdf",
        "action_note": "Evidence requested: low-resolution photos require daylight replacement.",
        "request_message": "We could not clearly verify the property damage from the photos provided. Please upload clear, well-lit photos taken with your mobile camera showing the entire damaged area."
    },
    {
        "id": "claim_demo_04",
        "claimant_user_id": "user_sunita",
        "claimant_name": "Sunita Sharma",
        "policy_number": "POL-HLT-9182",
        "claim_type": "health",
        "peril": "hospitalisation",
        "incident_date": "2026-06-25",
        "incident_time": "09:15",
        "claimed_amount": 145000.0,
        "variant": "HIGH",
        "status": "under_review",
        "fast_track": 0,
        "photo": "03_edited_spliced_photo.jpg",
        "doc": "hospital_bill.pdf",
        "action_note": "Hospital bill discrepancy flagged for forensic audit."
    },
    {
        "id": "claim_demo_05",
        "claimant_user_id": "user_sunita",
        "claimant_name": "Sunita Sharma",
        "policy_number": "POL-MOT-3319",
        "claim_type": "motor",
        "peril": "theft_attempt",
        "incident_date": "2026-08-01",
        "incident_time": "22:10",
        "claimed_amount": 18000.0,
        "variant": "LOW",
        "status": "under_review",
        "fast_track": 0,
        "photo": "02_genuine_phone_photo.jpg",
        "doc": "scanned_invoice.jpg",
        "action_note": "Submitted and under triage queue."
    },
    {
        "id": "claim_demo_06",
        "claimant_user_id": "user_sunita",
        "claimant_name": "Sunita Sharma",
        "policy_number": "POL-HLT-9182",
        "claim_type": "health",
        "peril": "day_care_procedure",
        "incident_date": "2026-08-12",
        "incident_time": "15:00",
        "claimed_amount": 22000.0,
        "variant": "LOW",
        "status": "approved",
        "fast_track": 0,
        "photo": None,
        "doc": "clean_invoice.pdf",
        "action_note": "Claim approved after medical team review."
    }
]

def seed_demo_claims(force: bool = False):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM claims")
    if c.fetchone()[0] > 0 and not force:
        conn.close()
        return
    now = datetime.utcnow().isoformat()

    for item in DEMO_CLAIMS_CONFIG:
        cid = item["id"]
        existing = get_claim_record(cid)
        if existing and not force:
            continue

        # Copy sample files
        claim_files_dir = os.path.join(CLAIMS_RUNTIME, cid)
        os.makedirs(claim_files_dir, exist_ok=True)
        dest_photo = None
        dest_doc = None

        if item.get("photo"):
            src_photo = os.path.join(SAMPLES_DIR, item["photo"])
            if os.path.exists(src_photo):
                dest_photo = os.path.join(claim_files_dir, item["photo"])
                shutil.copy2(src_photo, dest_photo)
                add_claim_evidence_item({
                    "claim_id": cid,
                    "slot": "damage_closeup",
                    "file_label": item["photo"],
                    "file_path": dest_photo,
                    "capture_source": "camera" if item["variant"] == "LOW" else "upload",
                    "state": "needs_replacing" if item["status"] == "needs_evidence" else "checked",
                    "created_at": now,
                    "updated_at": now
                })

        if item.get("doc"):
            src_doc = os.path.join(SAMPLES_DIR, "docs", item["doc"])
            if os.path.exists(src_doc):
                dest_doc = os.path.join(claim_files_dir, item["doc"])
                shutil.copy2(src_doc, dest_doc)
                add_claim_evidence_item({
                    "claim_id": cid,
                    "slot": "repair_estimate",
                    "file_label": item["doc"],
                    "file_path": dest_doc,
                    "capture_source": "upload",
                    "state": "checked",
                    "created_at": now,
                    "updated_at": now
                })

        meta_dict = {
            "claim_id": cid,
            "incident_date": item["incident_date"],
            "claimed_amount": item["claimed_amount"],
            "policy_number": item["policy_number"]
        }

        # Run REAL orchestrator pipeline for live demo claims (CLM-001..004)
        is_live_demo = cid in ("claim_demo_01", "claim_demo_02", "claim_demo_03", "claim_demo_04")
        if is_live_demo:
            job_id = f"job_{cid}"
            payload = {
                "claim_id": cid,
                "claimant_id": item["claimant_user_id"],
                "images": [dest_photo] if dest_photo else [],
                "document": dest_doc if dest_doc else None,
                "metadata": meta_dict
            }
            res = asyncio.run(_execute_analysis_job(job_id, "claim", payload))
            result_id = res.id if res else f"res_{cid}"
        else:
            # Synthetic history claims
            result_id = f"res_{cid}"
            result_payload = get_canned_result(variant=item["variant"], result_id=result_id)
            c.execute("""
                INSERT INTO results (
                    id, job_id, mode, overall_risk, overall_band,
                    image_risk, document_risk, identity_risk, summary, json, created_at, is_seed, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synthetic_history')
                ON CONFLICT(id) DO UPDATE SET
                    job_id=excluded.job_id,
                    mode=excluded.mode,
                    overall_risk=excluded.overall_risk,
                    overall_band=excluded.overall_band,
                    image_risk=excluded.image_risk,
                    document_risk=excluded.document_risk,
                    identity_risk=excluded.identity_risk,
                    summary=excluded.summary,
                    json=excluded.json,
                    data_source=excluded.data_source
            """, (
                result_id,
                f"job_{cid}",
                "claim",
                result_payload.overall.risk,
                result_payload.overall.band,
                result_payload.image.risk if result_payload.image else 0.0,
                result_payload.document.risk if result_payload.document else 0.0,
                0.0,
                result_payload.overall.summary,
                result_payload.model_dump_json(),
                now,
                1
            ))

        # Save claim record with ON CONFLICT DO UPDATE
        c.execute("""
            INSERT INTO claims (
                id, claimant_user_id, policy_number, claimant_name, claim_type, peril,
                incident_date, incident_time, incident_location_json, claimed_amount,
                damaged_items_json, description_text, description_lang, consent, status,
                result_id, result_ids_json, fast_track, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                claimant_user_id=excluded.claimant_user_id,
                policy_number=excluded.policy_number,
                claimant_name=excluded.claimant_name,
                claim_type=excluded.claim_type,
                peril=excluded.peril,
                incident_date=excluded.incident_date,
                incident_time=excluded.incident_time,
                incident_location_json=excluded.incident_location_json,
                claimed_amount=excluded.claimed_amount,
                damaged_items_json=excluded.damaged_items_json,
                description_text=excluded.description_text,
                description_lang=excluded.description_lang,
                consent=excluded.consent,
                status=excluded.status,
                result_id=excluded.result_id,
                result_ids_json=excluded.result_ids_json,
                fast_track=excluded.fast_track,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
        """, (
            cid,
            item["claimant_user_id"],
            item["policy_number"],
            item["claimant_name"],
            item["claim_type"],
            item["peril"],
            item["incident_date"],
            item["incident_time"],
            json.dumps({"city": "Bengaluru"}),
            item["claimed_amount"],
            json.dumps(["Front Bumper", "Headlight"]),
            f"Accidental damage occurred on {item['incident_date']}.",
            "en",
            1,
            item["status"],
            result_id,
            json.dumps([result_id]),
            item["fast_track"],
            json.dumps(meta_dict),
            now,
            now
        ))

        # Add action record
        add_action_record({
            "claim_id": cid,
            "result_id": result_id,
            "actor": "Pooja Mehta" if item["status"] != "under_review" else "system",
            "action": "fast_track" if item["fast_track"] else ("request_evidence" if item["status"] == "needs_evidence" else "analysis_completed"),
            "from_status": "submitted",
            "to_status": item["status"],
            "reason_category": "photo_unclear" if item["status"] == "needs_evidence" else "other",
            "claimant_message": item.get("request_message", ""),
            "internal_note": item["action_note"],
            "message_source": "template",
            "draft_edited": 0,
            "slots_to_resubmit_json": json.dumps(["damage_closeup"]) if item["status"] == "needs_evidence" else "[]",
            "created_at": now
        })

    conn.commit()
    conn.close()
    print("Demo claims seeded successfully.")

def make_exif_image(dest_path: str, date_str: str = None, gps_coords: tuple = None, crop_and_color: bool = False):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    arr = np.zeros((400, 600, 3), dtype=np.uint8)
    arr[:, :] = [180, 190, 205]
    arr[160:320, 80:520] = [30, 80, 180]
    arr[120:200, 160:440] = [20, 60, 150]
    arr[130:190, 180:420] = [200, 230, 255]
    arr[290:350, 140:200] = [20, 20, 20]
    arr[290:350, 400:460] = [20, 20, 20]
    arr[220:270, 460:510] = [15, 35, 90]
    img = Image.fromarray(arr)

    if crop_and_color:
        w, h = img.size
        img = img.crop((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)))
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.25)
        bright = ImageEnhance.Brightness(img)
        img = bright.enhance(1.1)

    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    has_exif = False

    if date_str:
        has_exif = True
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str.encode("utf-8")

    if gps_coords:
        has_exif = True
        lat, lng = gps_coords
        lat_ref = "N" if lat >= 0 else "S"
        lng_ref = "E" if lng >= 0 else "W"
        lat_abs = abs(lat)
        lng_abs = abs(lng)
        lat_d = int(lat_abs)
        lat_m = int((lat_abs - lat_d) * 60)
        lat_s = int(round(((lat_abs - lat_d) * 60 - lat_m) * 60 * 100))
        lng_d = int(lng_abs)
        lng_m = int((lng_abs - lng_d) * 60)
        lng_s = int(round(((lng_abs - lng_d) * 60 - lng_m) * 60 * 100))
        exif_dict["GPS"] = {
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLatitude: ((lat_d, 1), (lat_m, 1), (lat_s, 100)),
            piexif.GPSIFD.GPSLongitudeRef: lng_ref,
            piexif.GPSIFD.GPSLongitude: ((lng_d, 1), (lng_m, 1), (lng_s, 100))
        }

    if has_exif:
        exif_bytes = piexif.dump(exif_dict)
        img.save(dest_path, "JPEG", exif=exif_bytes, quality=90)
    else:
        img.save(dest_path, "JPEG", quality=90)
    return dest_path

def seed_prompt8_fraud_scenarios(force: bool = False):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()

    # 1. Scenario A: Genuine Car Claim (Ravi)
    cid_a = "claim_demo_07"
    claim_files_a = os.path.join(CLAIMS_RUNTIME, cid_a)
    photo_a = make_exif_image(os.path.join(claim_files_a, "car_genuine.jpg"))
    res_a_id = f"res_{cid_a}"
    if not get_claim_record(cid_a) or force:
        index_image(
            image_path=photo_a,
            claim_id=cid_a,
            claimant_id="user_ravi",
            result_id=res_a_id,
            slot="full_vehicle"
        )
        res_a_obj = get_canned_result(variant="LOW", result_id=res_a_id)
        c.execute("""
            INSERT INTO results (
                id, job_id, mode, overall_risk, overall_band, image_risk, document_risk,
                identity_risk, summary, json, created_at, is_seed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                job_id=excluded.job_id,
                mode=excluded.mode,
                overall_risk=excluded.overall_risk,
                overall_band=excluded.overall_band,
                image_risk=excluded.image_risk,
                document_risk=excluded.document_risk,
                identity_risk=excluded.identity_risk,
                summary=excluded.summary,
                json=excluded.json,
                is_seed=excluded.is_seed
        """, (
            res_a_id, f"job_{cid_a}", "claim", 0.08, "LOW", 0.05, 0.08, 0.0,
            "LOW fraud likelihood (8%). Genuine vehicle submission.",
            res_a_obj.model_dump_json(), "2026-06-15T10:00:00", 1
        ))
        c.execute("""
            INSERT INTO claims (
                id, claimant_user_id, policy_number, claimant_name, claim_type, peril,
                incident_date, incident_time, incident_location_json, claimed_amount,
                damaged_items_json, description_text, description_lang, consent, status,
                result_id, result_ids_json, fast_track, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                claimant_user_id=excluded.claimant_user_id,
                policy_number=excluded.policy_number,
                claimant_name=excluded.claimant_name,
                claim_type=excluded.claim_type,
                peril=excluded.peril,
                incident_date=excluded.incident_date,
                incident_time=excluded.incident_time,
                incident_location_json=excluded.incident_location_json,
                claimed_amount=excluded.claimed_amount,
                damaged_items_json=excluded.damaged_items_json,
                description_text=excluded.description_text,
                description_lang=excluded.description_lang,
                consent=excluded.consent,
                status=excluded.status,
                result_id=excluded.result_id,
                result_ids_json=excluded.result_ids_json,
                fast_track=excluded.fast_track,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
        """, (
            cid_a, "user_ravi", "POL-MOT-8821", "Ravi Kumar", "motor", "collision",
            "2026-06-15", "10:30", json.dumps({"lat": 12.9716, "lng": 77.5946, "text": "MG Road, Bengaluru"}),
            45000.0, json.dumps(["Front Bumper"]), "Collision near signal.", "en", 1, "approved",
            res_a_id, json.dumps([res_a_id]), 1, json.dumps({"incident_date": "2026-06-15"}),
            "2026-06-15T11:00:00", "2026-06-15T11:00:00"
        ))
        add_claim_evidence_item({
            "claim_id": cid_a, "slot": "full_vehicle", "file_label": "car_genuine.jpg",
            "file_path": photo_a, "capture_source": "camera", "state": "checked",
            "created_at": now, "updated_at": now
        })

    # 2. Scenario B: Recycled/Cropped/Recoloured Car Photo across Different Claimants (Sunita)
    cid_b = "claim_demo_08"
    if not get_claim_record(cid_b) or force:
        claim_files_b = os.path.join(CLAIMS_RUNTIME, cid_b)
        photo_b = make_exif_image(os.path.join(claim_files_b, "car_reused_cropped.jpg"), crop_and_color=True)
        res_b_id = f"res_{cid_b}"
        dup_ev = Evidence(
            id="IMG-DUP-02",
            kind="risk",
            raw_score=0.96,
            calibrated_score=0.96,
            weight=0.85,
            effective_weight=0.85,
            severity="critical",
            title="Evidence Reused Across Different Claimants",
            reason=f"Identical image submitted in earlier claim {cid_a} on 15 Jun 2026 by Ravi Kumar (Masked).",
            details={
                "other_claim_id": cid_a,
                "other_claimant": "R*** K****",
                "match_type": "cropped & recoloured",
                "similarity": 0.96,
                "thumbnail_current": f"/api/v1/artifacts/{res_b_id}/thumb_full_vehicle.jpg",
                "thumbnail_earlier": f"/api/v1/artifacts/{res_a_id}/thumb_full_vehicle.jpg"
            },
            pipeline_input="img_1",
            page=1,
            contribution=0.85,
            contribution_pct=92.4,
            rank=1
        )
        res_b_obj = AnalysisResult(
            id=res_b_id,
            mode="claim",
            created_at=now,
            overall=OverallScore(
                risk=0.92,
                band="HIGH",
                confidence="high",
                summary="CRITICAL fraud likelihood (92%). Reused image detected across different claimants."
            ),
            image=PipelineScore(pipeline="image", risk=0.92, authenticity=0.08, band="HIGH", confidence="high", evidence_ids=["IMG-DUP-02"]),
            evidence=[dup_ev],
            detector_status=[DetectorStatus(detector="img_1:duplicates", status="ok", duration_ms=45)],
            checks_run=[CheckRunItem(detector="img_1:duplicates", status="ok", duration_ms=45, reason="Cross-claim duplicate image detected")],
            quality_warnings=[],
            artifacts={
                "preview_image": f"/api/v1/artifacts/{res_b_id}/preview_img_1.jpg",
                "pages": []
            },
            versions={"engine": "lucen-2.0", "detector": "clip-vit-base-patch32", "calibration_date": "2026-10-02"},
            why_this_score=WhyThisScore(
                image=PipelineWhy(evidence_contributions=[], formula="Override rule O4 floor to 0.90", overrides_applied=["Override rule O4: Cross-claim duplicate image floors image risk at 0.90."]),
                overall=OverallWhy(formula="0.7 * 0.92 + 0.3 * 0.92 = 0.920", pipeline_risks={"image": 0.92})
            ),
            top_reasons=[f"Identical image submitted in earlier claim {cid_a} on 15 Jun 2026 by Ravi Kumar."],
            recommended_action="Refer claim to SIU (Special Investigation Unit) for syndicate fraud inquiry.",
            summary_source="template"
        )
        c.execute("""
            INSERT INTO results (
                id, job_id, mode, overall_risk, overall_band, image_risk, document_risk,
                identity_risk, summary, json, created_at, is_seed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                job_id=excluded.job_id,
                mode=excluded.mode,
                overall_risk=excluded.overall_risk,
                overall_band=excluded.overall_band,
                image_risk=excluded.image_risk,
                document_risk=excluded.document_risk,
                identity_risk=excluded.identity_risk,
                summary=excluded.summary,
                json=excluded.json,
                is_seed=excluded.is_seed
        """, (
            res_b_id, f"job_{cid_b}", "claim", 0.92, "HIGH", 0.92, 0.0, 0.0,
            res_b_obj.overall.summary, res_b_obj.model_dump_json(), now, 1
        ))
        c.execute("""
            INSERT INTO claims (
                id, claimant_user_id, policy_number, claimant_name, claim_type, peril,
                incident_date, incident_time, incident_location_json, claimed_amount,
                damaged_items_json, description_text, description_lang, consent, status,
                result_id, result_ids_json, fast_track, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                claimant_user_id=excluded.claimant_user_id,
                policy_number=excluded.policy_number,
                claimant_name=excluded.claimant_name,
                claim_type=excluded.claim_type,
                peril=excluded.peril,
                incident_date=excluded.incident_date,
                incident_time=excluded.incident_time,
                incident_location_json=excluded.incident_location_json,
                claimed_amount=excluded.claimed_amount,
                damaged_items_json=excluded.damaged_items_json,
                description_text=excluded.description_text,
                description_lang=excluded.description_lang,
                consent=excluded.consent,
                status=excluded.status,
                result_id=excluded.result_id,
                result_ids_json=excluded.result_ids_json,
                fast_track=excluded.fast_track,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
        """, (
            cid_b, "user_sunita", "POL-MOT-3319", "Sunita Sharma", "motor", "collision",
            "2026-07-20", "15:00", json.dumps({"lat": 19.0760, "lng": 72.8777, "text": "Bandra, Mumbai"}),
            52000.0, json.dumps(["Front Bumper"]), "Minor collision in traffic.", "en", 1, "under_review",
            res_b_id, json.dumps([res_b_id]), 0, json.dumps({"incident_date": "2026-07-20"}),
            now, now
        ))
        add_claim_evidence_item({
            "claim_id": cid_b, "slot": "full_vehicle", "file_label": "car_reused_cropped.jpg",
            "file_path": photo_b, "capture_source": "upload", "state": "checked",
            "created_at": now, "updated_at": now
        })

    # 3. Scenario C: Photo EXIF Date Before Stated Incident Date (CLM-X-01)
    cid_c = "claim_demo_09"
    if not get_claim_record(cid_c) or force:
        claim_files_c = os.path.join(CLAIMS_RUNTIME, cid_c)
        photo_c = make_exif_image(os.path.join(claim_files_c, "car_old_date.jpg"), date_str="2024:01:05 10:30:00")
        res_c_id = f"res_{cid_c}"
        date_ev = Evidence(
            id="CLM-X-01",
            pipeline="claim",
            source="rules",
            kind="risk",
            raw_score=0.85,
            calibrated_score=0.85,
            weight=0.80,
            effective_weight=0.80,
            severity="high",
            title="Photo Timestamp Precedes Incident",
            reason="Photo metadata timestamp (2024-01-05 10:30:00) is 41 days before claimed incident date (2024-02-15).",
            details={
                "photo_date": "2024-01-05 10:30:00",
                "incident_date": "2024-02-15",
                "days_difference": 41
            },
            pipeline_input="img_1",
            page=1,
            contribution=0.80,
            contribution_pct=94.1,
            rank=1
        )
        res_c_obj = AnalysisResult(
            id=res_c_id,
            mode="claim",
            created_at=now,
            overall=OverallScore(
                risk=0.85,
                band="HIGH",
                confidence="high",
                summary="HIGH fraud likelihood (85%). The submitted photo was captured 41 days before the stated incident date."
            ),
            image=PipelineScore(pipeline="image", risk=0.10, authenticity=0.90, band="LOW", confidence="high", evidence_ids=[]),
            evidence=[date_ev],
            detector_status=[DetectorStatus(detector="claim:check_photo_incident_date", status="ok", duration_ms=20)],
            checks_run=[CheckRunItem(detector="claim:check_photo_incident_date", status="ok", duration_ms=20, reason="Photo timestamp (05 Jan 2024) is 41 days prior to incident (15 Feb 2024)")],
            quality_warnings=[],
            artifacts={"pages": []},
            versions={"engine": "lucen-2.0", "detector": "clip-vit-base-patch32", "calibration_date": "2026-10-02"},
            why_this_score=WhyThisScore(
                overall=OverallWhy(formula="0.7 * 0.85 + 0.3 * 0.47 = 0.850", pipeline_risks={"claim": 0.85, "image": 0.10})
            ),
            top_reasons=["Photo metadata timestamp (2024-01-05) is 41 days before claimed incident date (2024-02-15)."],
            recommended_action="Request immediate explanation from policyholder regarding discrepancy in photo capture date.",
            summary_source="template"
        )
        c.execute("""
            INSERT INTO results (
                id, job_id, mode, overall_risk, overall_band, image_risk, document_risk,
                identity_risk, summary, json, created_at, is_seed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                job_id=excluded.job_id,
                mode=excluded.mode,
                overall_risk=excluded.overall_risk,
                overall_band=excluded.overall_band,
                image_risk=excluded.image_risk,
                document_risk=excluded.document_risk,
                identity_risk=excluded.identity_risk,
                summary=excluded.summary,
                json=excluded.json,
                is_seed=excluded.is_seed
        """, (
            res_c_id, f"job_{cid_c}", "claim", 0.85, "HIGH", 0.10, 0.0, 0.0,
            res_c_obj.overall.summary, res_c_obj.model_dump_json(), now, 1
        ))
        c.execute("""
            INSERT INTO claims (
                id, claimant_user_id, policy_number, claimant_name, claim_type, peril,
                incident_date, incident_time, incident_location_json, claimed_amount,
                damaged_items_json, description_text, description_lang, consent, status,
                result_id, result_ids_json, fast_track, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                claimant_user_id=excluded.claimant_user_id,
                policy_number=excluded.policy_number,
                claimant_name=excluded.claimant_name,
                claim_type=excluded.claim_type,
                peril=excluded.peril,
                incident_date=excluded.incident_date,
                incident_time=excluded.incident_time,
                incident_location_json=excluded.incident_location_json,
                claimed_amount=excluded.claimed_amount,
                damaged_items_json=excluded.damaged_items_json,
                description_text=excluded.description_text,
                description_lang=excluded.description_lang,
                consent=excluded.consent,
                status=excluded.status,
                result_id=excluded.result_id,
                result_ids_json=excluded.result_ids_json,
                fast_track=excluded.fast_track,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
        """, (
            cid_c, "user_ravi", "POL-MOT-8821", "Ravi Kumar", "motor", "collision",
            "2024-02-15", "14:00", json.dumps({"city": "Bengaluru"}),
            38000.0, json.dumps(["Bumper"]), "Vehicle hit while parked.", "en", 1, "under_review",
            res_c_id, json.dumps([res_c_id]), 0, json.dumps({"incident_date": "2024-02-15"}),
            now, now
        ))
        add_claim_evidence_item({
            "claim_id": cid_c, "slot": "damage_front", "file_label": "car_old_date.jpg",
            "file_path": photo_c, "capture_source": "camera", "state": "checked",
            "created_at": now, "updated_at": now
        })

    # 4. Scenario D: Photo GPS (Bangalore) vs Stated Incident Location (Mumbai) (CLM-X-06)
    cid_d = "claim_demo_10"
    if not get_claim_record(cid_d) or force:
        claim_files_d = os.path.join(CLAIMS_RUNTIME, cid_d)
        photo_d = make_exif_image(os.path.join(claim_files_d, "car_bangalore_gps.jpg"), gps_coords=(12.9716, 77.5946))
        res_d_id = f"res_{cid_d}"
        gps_ev = Evidence(
            id="CLM-X-06",
            pipeline="claim",
            source="rules",
            kind="risk",
            raw_score=0.85,
            calibrated_score=0.85,
            weight=0.75,
            effective_weight=0.75,
            severity="high",
            title="Photo GPS Discrepancy",
            reason="Photo GPS coordinates (12.9716, 77.5946 - Bengaluru) are 842.1 km away from claimed incident location (19.0760, 72.8777 - Nariman Point, Mumbai).",
            details={
                "photo_lat": 12.9716,
                "photo_lng": 77.5946,
                "claimed_lat": 19.0760,
                "claimed_lng": 72.8777,
                "distance_km": 842.1
            },
            pipeline_input="img_1",
            page=1,
            contribution=0.75,
            contribution_pct=91.5,
            rank=1
        )
        res_d_obj = AnalysisResult(
            id=res_d_id,
            mode="claim",
            created_at=now,
            overall=OverallScore(
                risk=0.82,
                band="HIGH",
                confidence="high",
                summary="HIGH fraud likelihood (82%). Photo EXIF GPS location is 842 km away from claimed accident site."
            ),
            evidence=[gps_ev],
            detector_status=[DetectorStatus(detector="claim:check_photo_gps_location", status="ok", duration_ms=15)],
            checks_run=[CheckRunItem(detector="claim:check_photo_gps_location", status="ok", duration_ms=15, reason="Photo GPS (12.9716, 77.5946) is 842.1 km away from claimed location (19.0760, 72.8777)")],
            quality_warnings=[],
            artifacts={
                "location": {
                    "claimed": {"lat": 19.0760, "lng": 72.8777, "text": "Nariman Point, Mumbai"},
                    "photos": [{"image": "car_bangalore_gps.jpg", "lat": 12.9716, "lng": 77.5946, "distance_km": 842.1}],
                    "max_distance_km": 842.1
                },
                "pages": []
            },
            versions={"engine": "lucen-2.0", "detector": "clip-vit-base-patch32", "calibration_date": "2026-10-02"},
            why_this_score=WhyThisScore(
                overall=OverallWhy(formula="0.7 * 0.85 + 0.3 * 0.75 = 0.820", pipeline_risks={"claim": 0.82})
            ),
            top_reasons=["Photo GPS coordinates are 842.1 km away from claimed incident location in Mumbai."],
            recommended_action="Require live camera recapture with active device location services enabled.",
            summary_source="template"
        )
        c.execute("""
            INSERT INTO results (
                id, job_id, mode, overall_risk, overall_band, image_risk, document_risk,
                identity_risk, summary, json, created_at, is_seed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                job_id=excluded.job_id,
                mode=excluded.mode,
                overall_risk=excluded.overall_risk,
                overall_band=excluded.overall_band,
                image_risk=excluded.image_risk,
                document_risk=excluded.document_risk,
                identity_risk=excluded.identity_risk,
                summary=excluded.summary,
                json=excluded.json,
                is_seed=excluded.is_seed
        """, (
            res_d_id, f"job_{cid_d}", "claim", 0.82, "HIGH", 0.10, 0.0, 0.0,
            res_d_obj.overall.summary, res_d_obj.model_dump_json(), now, 1
        ))
        c.execute("""
            INSERT INTO claims (
                id, claimant_user_id, policy_number, claimant_name, claim_type, peril,
                incident_date, incident_time, incident_location_json, claimed_amount,
                damaged_items_json, description_text, description_lang, consent, status,
                result_id, result_ids_json, fast_track, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                claimant_user_id=excluded.claimant_user_id,
                policy_number=excluded.policy_number,
                claimant_name=excluded.claimant_name,
                claim_type=excluded.claim_type,
                peril=excluded.peril,
                incident_date=excluded.incident_date,
                incident_time=excluded.incident_time,
                incident_location_json=excluded.incident_location_json,
                claimed_amount=excluded.claimed_amount,
                damaged_items_json=excluded.damaged_items_json,
                description_text=excluded.description_text,
                description_lang=excluded.description_lang,
                consent=excluded.consent,
                status=excluded.status,
                result_id=excluded.result_id,
                result_ids_json=excluded.result_ids_json,
                fast_track=excluded.fast_track,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
        """, (
            cid_d, "user_sunita", "POL-MOT-3319", "Sunita Sharma", "motor", "collision",
            "2026-08-05", "18:00", json.dumps({"lat": 19.0760, "lng": 72.8777, "text": "Nariman Point, Mumbai"}),
            62000.0, json.dumps(["Rear Bumper"]), "Rear collision at signal.", "en", 1, "under_review",
            res_d_id, json.dumps([res_d_id]), 0, json.dumps({"incident_date": "2026-08-05"}),
            now, now
        ))
        add_claim_evidence_item({
            "claim_id": cid_d, "slot": "damage_rear", "file_label": "car_bangalore_gps.jpg",
            "file_path": photo_d, "capture_source": "camera", "state": "checked",
            "created_at": now, "updated_at": now
        })

    # 5. Scenario E: Repair Bill Total (45k) != Claimed Amount (75k) (CLM-X-02)
    cid_e = "claim_demo_11"
    if not get_claim_record(cid_e) or force:
        res_e_id = f"res_{cid_e}"
        amt_ev = Evidence(
            id="CLM-X-02",
            pipeline="claim",
            source="rules",
            kind="risk",
            raw_score=0.75,
            calibrated_score=0.75,
            weight=0.60,
            effective_weight=0.60,
            severity="high",
            title="Claim Amount Exceeds Verified Invoice",
            reason="Claimed amount (75,000 INR) exceeds verified repair invoice (45,000 INR) by 30,000 INR (66.7%).",
            details={
                "claimed_amount": 75000.0,
                "doc_total": 45000.0,
                "delta": 30000.0,
                "delta_pct": 66.7
            },
            pipeline_input="doc",
            page=1,
            contribution=0.60,
            contribution_pct=88.2,
            rank=1
        )
        res_e_obj = AnalysisResult(
            id=res_e_id,
            mode="claim",
            created_at=now,
            overall=OverallScore(
                risk=0.78,
                band="HIGH",
                confidence="high",
                summary="HIGH fraud likelihood (78%). Stated claim amount (INR 75,000) significantly exceeds verified invoice total (INR 45,000)."
            ),
            evidence=[amt_ev],
            detector_status=[DetectorStatus(detector="claim:check_amount_match", status="ok", duration_ms=10)],
            checks_run=[CheckRunItem(detector="claim:check_amount_match", status="ok", duration_ms=10, reason="Claimed amount (75,000) exceeds document total (45,000) by 30,000 INR")],
            quality_warnings=[],
            artifacts={"pages": []},
            versions={"engine": "lucen-2.0", "detector": "clip-vit-base-patch32", "calibration_date": "2026-10-02"},
            why_this_score=WhyThisScore(
                overall=OverallWhy(formula="0.7 * 0.78 + 0.3 * 0.78 = 0.780", pipeline_risks={"claim": 0.78})
            ),
            top_reasons=["Claimed amount (75,000 INR) exceeds verified repair invoice (45,000 INR) by 30,000 INR (66.7%)."],
            recommended_action="Adjust claimed settlement figure down to INR 45,000.00 as per verified invoice.",
            summary_source="template"
        )
        c.execute("""
            INSERT INTO results (
                id, job_id, mode, overall_risk, overall_band, image_risk, document_risk,
                identity_risk, summary, json, created_at, is_seed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                job_id=excluded.job_id,
                mode=excluded.mode,
                overall_risk=excluded.overall_risk,
                overall_band=excluded.overall_band,
                image_risk=excluded.image_risk,
                document_risk=excluded.document_risk,
                identity_risk=excluded.identity_risk,
                summary=excluded.summary,
                json=excluded.json,
                is_seed=excluded.is_seed
        """, (
            res_e_id, f"job_{cid_e}", "claim", 0.78, "HIGH", 0.0, 0.40, 0.0,
            res_e_obj.overall.summary, res_e_obj.model_dump_json(), now, 1
        ))
        c.execute("""
            INSERT INTO claims (
                id, claimant_user_id, policy_number, claimant_name, claim_type, peril,
                incident_date, incident_time, incident_location_json, claimed_amount,
                damaged_items_json, description_text, description_lang, consent, status,
                result_id, result_ids_json, fast_track, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                claimant_user_id=excluded.claimant_user_id,
                policy_number=excluded.policy_number,
                claimant_name=excluded.claimant_name,
                claim_type=excluded.claim_type,
                peril=excluded.peril,
                incident_date=excluded.incident_date,
                incident_time=excluded.incident_time,
                incident_location_json=excluded.incident_location_json,
                claimed_amount=excluded.claimed_amount,
                damaged_items_json=excluded.damaged_items_json,
                description_text=excluded.description_text,
                description_lang=excluded.description_lang,
                consent=excluded.consent,
                status=excluded.status,
                result_id=excluded.result_id,
                result_ids_json=excluded.result_ids_json,
                fast_track=excluded.fast_track,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
        """, (
            cid_e, "user_ravi", "POL-MOT-8821", "Ravi Kumar", "motor", "collision",
            "2026-08-10", "11:30", json.dumps({"city": "Bengaluru"}),
            75000.0, json.dumps(["Windshield", "Bumper"]), "Accidental damage repair claim.", "en", 1, "under_review",
            res_e_id, json.dumps([res_e_id]), 0, json.dumps({"incident_date": "2026-08-10"}),
            now, now
        ))

    conn.commit()
    conn.close()
    print("Prompt 8 fraud scenarios seeded successfully.")

if __name__ == "__main__":
    seed_demo_claims()
    seed_prompt8_fraud_scenarios()
