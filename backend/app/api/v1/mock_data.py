from typing import Dict, Any, List
from ...schemas.result import (
    AnalysisResult, OverallScore, PipelineScore, DetectorStatus,
    QualityWarning, ChallengeStatus, LivenessStatus, QrComparison,
    AadhaarQrStatus, StoryStatus, Link, Decision, WhyThisScore,
    WhyThisScoreItem, PipelineWhy, OverallWhy, CheckRunItem
)
from ...schemas.evidence import Evidence, BBox

def get_canned_result(variant: str = "HIGH", result_id: str = "mock-result-HIGH") -> AnalysisResult:
    variant = variant.upper()
    if "LOW" in variant:
        ev = [
            Evidence(
                id="IMG-EXIF-01",
                kind="info",
                raw_score=0.10,
                calibrated_score=0.10,
                weight=0.10,
                effective_weight=0.10,
                severity="low",
                title="Camera Metadata Present",
                reason="Standard smartphone camera metadata found (Apple iPhone 14 Pro).",
                details={"Make": "Apple", "Model": "iPhone 14 Pro"},
                pipeline_input="img_1",
                page=1,
                contribution=0.0,
                contribution_pct=0.0,
                rank=None
            )
        ]
        img_score = PipelineScore(
            pipeline="image",
            risk=0.05,
            authenticity=0.95,
            band="LOW",
            confidence="high",
            evidence_ids=["IMG-EXIF-01"]
        )
        doc_score = PipelineScore(
            pipeline="document",
            risk=0.08,
            authenticity=0.92,
            band="LOW",
            confidence="high",
            evidence_ids=[]
        )
        det_status = [
            DetectorStatus(detector="img_1:ai_detector", status="ok", duration_ms=180),
            DetectorStatus(detector="img_1:ela", status="ok", duration_ms=90),
            DetectorStatus(detector="doc:document_rules", status="ok", duration_ms=30)
        ]
        checks_run = [
            CheckRunItem(detector=d.detector, status=d.status, duration_ms=d.duration_ms, reason=d.error)
            for d in det_status
        ]
        return AnalysisResult(
            id=result_id,
            mode="claim",
            created_at="2026-10-03T10:00:00Z",
            overall=OverallScore(
                risk=0.08,
                band="LOW",
                confidence="high",
                summary="LOW fraud likelihood (8%). No anomalous patterns or tamper artifacts were detected. Recommended action: Approve claim for automated Straight-Through Processing (STP)."
            ),
            image=img_score,
            document=doc_score,
            image_results=[img_score],
            evidence=ev,
            detector_status=det_status,
            checks_run=checks_run,
            quality_warnings=[],
            artifacts={
                "heatmap": f"/api/v1/artifacts/{result_id}/heatmap.json",
                "preview_img_1": f"/api/v1/artifacts/{result_id}/preview_img_1.jpg",
                "pages": []
            },
            versions={
                "detector": "Ateeqq/ai-vs-human-image-detector",
                "calibration_date": "2026-10-02",
                "git_commit": "e8d47bf",
                "engine": "lucen-2.0"
            },
            why_this_score=WhyThisScore(
                image=PipelineWhy(
                    evidence_contributions=[],
                    formula="No participating risk signals = 0.050",
                    overrides_applied=[],
                    quality_gates_applied=[]
                ),
                document=PipelineWhy(
                    evidence_contributions=[],
                    formula="No participating risk signals = 0.080",
                    overrides_applied=[],
                    quality_gates_applied=[]
                ),
                overall=OverallWhy(
                    formula="0.7 * max(0.080) + 0.3 * mean(0.065) = 0.080",
                    pipeline_risks={"image": 0.05, "document": 0.08},
                    overrides_applied=[]
                )
            ),
            top_reasons=["All automated forensic integrity checks passed with no indicators of manipulation."],
            recommended_action="Approve claim for automated Straight-Through Processing (STP).",
            summary_source="template",
            liveness=LivenessStatus(
                performed=True,
                passed=True,
                code_match=True,
                challenges=[
                    ChallengeStatus(name="turn_left", ok=True, ms=650),
                    ChallengeStatus(name="blink", ok=True, ms=320)
                ]
            ),
            aadhaar_qr=AadhaarQrStatus(
                found=True,
                signature_valid=True,
                mode="demo_key",
                comparisons=[
                    QrComparison(field="name", printed="Ravi Kumar", qr="Ravi Kumar", match=True),
                    QrComparison(field="dob", printed="1988-04-12", qr="1988-04-12", match=True)
                ],
                photo_similarity=0.92
            ),
            story=StoryStatus(
                contradictions=[],
                consistent_points=["Incident date matches invoice issue date"],
                source="llm"
            ),
            links=[]
        )
    elif "MED" in variant:
        ev = [
            Evidence(
                id="DOC-META-02",
                kind="risk",
                raw_score=0.50,
                calibrated_score=0.50,
                weight=0.15,
                effective_weight=0.15,
                severity="medium",
                title="PDF Modified After Creation",
                reason="The PDF was modified 14 days after it was created, using PDFtk.",
                details={"delta": "14 days", "producer": "PDFtk"},
                pipeline_input="doc",
                page=1,
                contribution=0.075,
                contribution_pct=100.0,
                rank=1
            )
        ]
        doc_score = PipelineScore(
            pipeline="document",
            risk=0.48,
            authenticity=0.52,
            band="MEDIUM",
            confidence="medium",
            evidence_ids=["DOC-META-02"]
        )
        det_status = [
            DetectorStatus(detector="doc:pdf_parser", status="ok", duration_ms=25),
            DetectorStatus(detector="doc:document_rules", status="ok", duration_ms=40)
        ]
        checks_run = [
            CheckRunItem(detector=d.detector, status=d.status, duration_ms=d.duration_ms, reason=d.error)
            for d in det_status
        ]
        return AnalysisResult(
            id=result_id,
            mode="claim",
            created_at="2026-10-03T10:00:00Z",
            overall=OverallScore(
                risk=0.48,
                band="MEDIUM",
                confidence="medium",
                summary="MEDIUM fraud likelihood (48%). The PDF was modified 14 days after creation. Recommended action: Route to senior claims adjuster for manual document review and verification of original invoice."
            ),
            document=doc_score,
            evidence=ev,
            detector_status=det_status,
            checks_run=checks_run,
            quality_warnings=[
                QualityWarning(code="RESOLUTION_LOW", message="Document scanned below 150 dpi.")
            ],
            artifacts={
                "heatmap": f"/api/v1/artifacts/{result_id}/heatmap.json",
                "preview_document": f"/api/v1/artifacts/{result_id}/preview_doc.pdf",
                "pages": []
            },
            versions={
                "detector": "Ateeqq/ai-vs-human-image-detector",
                "calibration_date": "2026-10-02",
                "git_commit": "e8d47bf",
                "engine": "lucen-2.0"
            },
            why_this_score=WhyThisScore(
                document=PipelineWhy(
                    evidence_contributions=[
                        WhyThisScoreItem(
                            evidence_id="DOC-META-02",
                            title="PDF Modified After Creation",
                            w=0.15,
                            p=0.50,
                            push=0.075,
                            contribution_pct=100.0
                        )
                    ],
                    formula="1 - (1 - 0.075) = 0.480",
                    overrides_applied=[],
                    quality_gates_applied=[]
                ),
                overall=OverallWhy(
                    formula="Single active pipeline (document) = 0.480",
                    pipeline_risks={"document": 0.48},
                    overrides_applied=[]
                )
            ),
            top_reasons=["The PDF was modified 14 days after it was created, using PDFtk."],
            recommended_action="Route to senior claims adjuster for manual document review and verification of original invoice.",
            summary_source="template",
            links=[]
        )
    else:  # HIGH
        ev = [
            Evidence(
                id="IMG-AI-01",
                kind="risk",
                raw_score=0.97,
                calibrated_score=0.97,
                weight=0.70,
                effective_weight=0.70,
                severity="high",
                title="AI-Generated Image",
                reason="The image shows strong patterns typical of AI generation.",
                details={"p": 0.97, "model": "SigLIP"},
                pipeline_input="img_1",
                page=1,
                contribution=0.524,
                contribution_pct=70.0,
                rank=1
            ),
            Evidence(
                id="DOC-LOGIC-01",
                kind="risk",
                raw_score=1.00,
                calibrated_score=1.00,
                weight=0.80,
                effective_weight=0.80,
                severity="high",
                title="Mathematical Mismatch",
                reason="The line items add up to 14,500.00 but stated total is 18,500.00.",
                field="total_amount",
                bbox=BBox(page=1, x=0.65, y=0.82, w=0.25, h=0.06),
                details={"expected": 14500.00, "found": 18500.00},
                pipeline_input="doc",
                page=1,
                contribution=0.50,
                contribution_pct=55.0,
                rank=2
            ),
            Evidence(
                id="DOC-CNN-01",
                kind="risk",
                raw_score=0.75,
                calibrated_score=0.75,
                weight=0.50,
                effective_weight=0.50,
                severity="medium",
                title="Tamper CNN Anomaly",
                reason="Tamper detector found an area around 'total_amount' with different compression pattern.",
                field="total_amount",
                bbox=BBox(page=1, x=0.64, y=0.81, w=0.27, h=0.08),
                details={"field": "total_amount", "confidence": 0.75},
                pipeline_input="doc",
                page=1,
                contribution=0.41,
                contribution_pct=45.0,
                rank=3
            ),
            Evidence(
                id="IMG-ELA-01",
                kind="risk",
                raw_score=0.70,
                calibrated_score=0.70,
                weight=0.25,
                effective_weight=0.25,
                severity="medium",
                title="ELA Compression Anomaly",
                reason="One region was compressed differently from the rest.",
                bbox=BBox(page=1, x=0.25, y=0.30, w=0.45, h=0.35),
                details={"difference": 0.70},
                pipeline_input="img_1",
                page=1,
                contribution=0.224,
                contribution_pct=30.0,
                rank=4
            )
        ]
        img_score = PipelineScore(
            pipeline="image",
            risk=0.75,
            authenticity=0.25,
            band="HIGH",
            confidence="high",
            evidence_ids=["IMG-AI-01", "IMG-ELA-01"]
        )
        doc_score = PipelineScore(
            pipeline="document",
            risk=0.91,
            authenticity=0.09,
            band="HIGH",
            confidence="high",
            evidence_ids=["DOC-LOGIC-01", "DOC-CNN-01"]
        )
        det_status = [
            DetectorStatus(detector="img_1:ai_detector", status="ok", duration_ms=210),
            DetectorStatus(detector="img_1:ela", status="ok", duration_ms=85),
            DetectorStatus(detector="doc:document_rules", status="ok", duration_ms=35),
            DetectorStatus(detector="doc:tamper_cnn", status="ok", duration_ms=190),
            DetectorStatus(detector="id_photo_match", status="skipped", duration_ms=0, error="skipped: not yet implemented"),
            DetectorStatus(detector="selfie_liveness", status="skipped", duration_ms=0, error="skipped: not yet implemented")
        ]
        checks_run = [
            CheckRunItem(detector=d.detector, status=d.status, duration_ms=d.duration_ms, reason=d.error)
            for d in det_status
        ]
        return AnalysisResult(
            id=result_id,
            mode="claim",
            created_at="2026-10-03T10:00:00Z",
            overall=OverallScore(
                risk=0.88,
                band="HIGH",
                confidence="high",
                summary="HIGH fraud likelihood (88%). The image shows strong patterns of AI generation. The line items add up to 14,500.00 but stated total is 18,500.00. Recommended action: Escalate to Special Investigation Unit (SIU) for detailed forensic document inspection and claimant interview."
            ),
            image=img_score,
            document=doc_score,
            image_results=[img_score],
            evidence=ev,
            detector_status=det_status,
            checks_run=checks_run,
            quality_warnings=[],
            artifacts={
                "heatmap": f"/api/v1/artifacts/{result_id}/heatmap.json",
                "preview_img_1": f"/api/v1/artifacts/{result_id}/preview_img_1.jpg",
                "preview_document": f"/api/v1/artifacts/{result_id}/preview_doc.pdf",
                "pages": [
                    {
                        "page": 1,
                        "width_pt": 595.0,
                        "height_pt": 842.0,
                        "image_url": f"/api/v1/artifacts/{result_id}/page_1.png",
                        "annotated_url": f"/api/v1/artifacts/{result_id}/page_1_boxes.png",
                        "tamper_heatmap_url": f"/api/v1/artifacts/{result_id}/page_1_tamper.png"
                    }
                ]
            },
            versions={
                "detector": "Ateeqq/ai-vs-human-image-detector",
                "calibration_date": "2026-10-02",
                "git_commit": "e8d47bf",
                "engine": "lucen-2.0"
            },
            why_this_score=WhyThisScore(
                image=PipelineWhy(
                    evidence_contributions=[
                        WhyThisScoreItem(
                            evidence_id="IMG-AI-01",
                            title="AI-Generated Image",
                            w=0.70,
                            p=0.97,
                            push=0.679,
                            contribution_pct=70.0
                        ),
                        WhyThisScoreItem(
                            evidence_id="IMG-ELA-01",
                            title="ELA Compression Anomaly",
                            w=0.25,
                            p=0.70,
                            push=0.175,
                            contribution_pct=30.0
                        )
                    ],
                    formula="1 - (1 - 0.679)(1 - 0.175) = 0.748",
                    overrides_applied=[],
                    quality_gates_applied=[]
                ),
                document=PipelineWhy(
                    evidence_contributions=[
                        WhyThisScoreItem(
                            evidence_id="DOC-LOGIC-01",
                            title="Mathematical Mismatch",
                            w=0.80,
                            p=1.00,
                            push=0.800,
                            contribution_pct=55.0
                        ),
                        WhyThisScoreItem(
                            evidence_id="DOC-CNN-01",
                            title="Tamper CNN Anomaly",
                            w=0.50,
                            p=0.75,
                            push=0.375,
                            contribution_pct=45.0
                        )
                    ],
                    formula="1 - (1 - 0.800)(1 - 0.375) = 0.905",
                    overrides_applied=[],
                    quality_gates_applied=[]
                ),
                overall=OverallWhy(
                    formula="0.7 * max(0.905, 0.748) + 0.3 * mean(0.905, 0.748) = 0.7 * 0.905 + 0.3 * 0.826 = 0.882",
                    pipeline_risks={"image": 0.748, "document": 0.905},
                    overrides_applied=[]
                )
            ),
            top_reasons=[
                "The image shows strong patterns typical of AI generation.",
                "The line items add up to 14,500.00 but stated total is 18,500.00.",
                "Tamper detector found an area around 'total_amount' with different compression pattern.",
                "One region was compressed differently from the rest."
            ],
            recommended_action="Escalate to Special Investigation Unit (SIU) for detailed forensic document inspection and claimant interview.",
            summary_source="template",
            liveness=LivenessStatus(
                performed=True,
                passed=False,
                code_match=False,
                challenges=[
                    ChallengeStatus(name="turn_left", ok=False, ms=1200)
                ]
            ),
            aadhaar_qr=AadhaarQrStatus(
                found=True,
                signature_valid=False,
                mode="demo_key",
                comparisons=[
                    QrComparison(field="name", printed="Sunil Verma", qr="Sunil Sharma", match=False)
                ],
                photo_similarity=0.42
            ),
            story=StoryStatus(
                contradictions=["Claimant stated accident occurred in Delhi; photo GPS coordinates place damage in Mumbai."],
                consistent_points=[],
                source="llm"
            ),
            links=[
                Link(result_id="CLM-2026-0881", reason="Identical vehicle damage photo used in earlier claim")
            ]
        )
