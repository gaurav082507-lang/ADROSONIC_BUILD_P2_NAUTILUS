/**
 * JSDoc type definitions matching docs/openapi.json and backend schemas.
 * Generated for Lucen AI Frontend.
 */

/**
 * @typedef {Object} BBox
 * @property {number} page
 * @property {number} x
 * @property {number} y
 * @property {number} w
 * @property {number} h
 */

/**
 * @typedef {Object} Evidence
 * @property {string} id
 * @property {string} kind - "risk" | "authenticity" | "info"
 * @property {number} raw_score
 * @property {number} calibrated_score
 * @property {number} weight
 * @property {number} effective_weight
 * @property {string} severity - "low" | "medium" | "high"
 * @property {string} title
 * @property {string} reason
 * @property {string} [field]
 * @property {BBox} [bbox]
 * @property {Object.<string, any>} [details]
 * @property {string} [artifact]
 */

/**
 * @typedef {Object} DetectorStatus
 * @property {string} detector
 * @property {string} status - "ok" | "skipped" | "failed"
 * @property {number} duration_ms
 * @property {string} [error]
 */

/**
 * @typedef {Object} PipelineScore
 * @property {string} pipeline - "image" | "document" | "identity" | "voice" | "claim"
 * @property {number} risk
 * @property {number} authenticity
 * @property {string} band - "LOW" | "MEDIUM" | "HIGH"
 * @property {string} confidence - "high" | "medium" | "low"
 * @property {string[]} evidence_ids
 */

/**
 * @typedef {Object} OverallScore
 * @property {number} risk
 * @property {string} band - "LOW" | "MEDIUM" | "HIGH"
 * @property {string} confidence - "high" | "medium" | "low"
 * @property {string} summary
 */

/**
 * @typedef {Object} QualityWarning
 * @property {string} code
 * @property {string} message
 */

/**
 * @typedef {Object} ChallengeStatus
 * @property {string} name
 * @property {boolean} ok
 * @property {number} ms
 */

/**
 * @typedef {Object} LivenessStatus
 * @property {boolean} performed
 * @property {boolean} passed
 * @property {boolean} code_match
 * @property {ChallengeStatus[]} challenges
 */

/**
 * @typedef {Object} QrComparison
 * @property {string} field
 * @property {string} printed
 * @property {string} qr
 * @property {boolean} match
 */

/**
 * @typedef {Object} AadhaarQrStatus
 * @property {boolean} found
 * @property {boolean} signature_valid
 * @property {string} mode - "uidai" | "demo_key"
 * @property {QrComparison[]} comparisons
 * @property {number} photo_similarity
 */

/**
 * @typedef {Object} StoryStatus
 * @property {string[]} contradictions
 * @property {string[]} consistent_points
 * @property {string} source
 */

/**
 * @typedef {Object} Link
 * @property {string} result_id
 * @property {string} reason
 */

/**
 * @typedef {Object} Decision
 * @property {string} status - "approved" | "rejected" | "info_requested"
 * @property {string} by
 * @property {string} at
 * @property {string} reason_code
 * @property {string} claimant_message
 * @property {string} internal_note
 */

/**
 * @typedef {Object} AnalysisResult
 * @property {string} id
 * @property {string} mode - "image" | "document" | "claim"
 * @property {string} created_at
 * @property {OverallScore} overall
 * @property {Evidence[]} evidence
 * @property {DetectorStatus[]} detector_status
 * @property {QualityWarning[]} quality_warnings
 * @property {Object.<string, any>} artifacts
 * @property {Object.<string, string>} versions
 * @property {PipelineScore} [image]
 * @property {PipelineScore} [document]
 * @property {PipelineScore} [voice]
 * @property {any} [identity]
 * @property {LivenessStatus} [liveness]
 * @property {AadhaarQrStatus} [aadhaar_qr]
 * @property {StoryStatus} [story]
 * @property {Link[]} [links]
 * @property {Decision} [decision]
 */

/**
 * @typedef {Object} StepStatus
 * @property {string} name
 * @property {string} status - "queued" | "running" | "done" | "failed"
 * @property {number} [duration_ms]
 */

/**
 * @typedef {Object} JobStatus
 * @property {string} job_id
 * @property {string} status - "queued" | "running" | "done" | "failed"
 * @property {string} mode - "image" | "document" | "claim"
 * @property {StepStatus[]} steps
 * @property {string} [result_id]
 * @property {string} [error]
 */

/**
 * @typedef {Object} ErrorDetail
 * @property {string} code
 * @property {string} message
 * @property {Object.<string, any>} [details]
 */

export {};
