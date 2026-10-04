import { z } from 'zod';
export const apiErrorSchema = z.object({
  error: z.object({ code: z.string(), message: z.string(), details: z.unknown().optional() }),
});
/*
 * Runtime checks for the REAL contract (contract/openapi.json). They are strict only on what the
 * UI cannot work without (ids, overall score, evidence list) and pass everything else through,
 * so additive backend changes never break the page.
 */
const bandSchema = z.string();
export const jobSchema = z
  .object({
    status: z.enum(['queued', 'running', 'done', 'failed']),
    steps: z.array(z.object({ name: z.string(), status: z.string() }).passthrough()).default([]),
    result_id: z.string().nullish(),
    error: z
      .union([z.string(), z.object({ message: z.string().optional() }).passthrough()])
      .nullish(),
  })
  .passthrough();
const scoreSchema = z
  .object({ risk: z.number(), band: bandSchema, confidence: z.string() })
  .passthrough();
export const resultSchema = z
  .object({
    id: z.string(),
    mode: z.string(),
    overall: scoreSchema,
    image: scoreSchema.nullish(),
    document: scoreSchema.nullish(),
    claim: scoreSchema.nullish(),
    evidence: z.array(z.object({ id: z.string() }).passthrough()),
    quality_warnings: z
      .array(z.union([z.string(), z.object({ message: z.string() }).passthrough()]))
      .default([]),
    artifacts: z.record(z.unknown()).nullish(),
  })
  .passthrough();

/* ---------- Network / analytics / voice (Prompt 9–10 contract) ---------- */
const graphNodeSchema = z
  .object({
    id: z.string(),
    type: z.string(),
    label: z.string(),
    band: bandSchema.optional(),
    risk: z.number().optional(),
    flags: z.array(z.string()).optional(),
    data_source: z.string().optional(),
  })
  .passthrough();
const graphEdgeSchema = z
  .object({
    id: z.string(),
    source: z.string(),
    target: z.string(),
    type: z.string(),
    strength: z.number(),
    label: z.string().optional(),
    evidence_ids: z.array(z.string()).optional(),
  })
  .passthrough();
export const graphSchema = z
  .object({
    nodes: z.array(graphNodeSchema),
    edges: z.array(graphEdgeSchema),
    rings: z
      .array(
        z.object({ ring_id: z.string(), ring_score: z.number(), member_ids: z.array(z.string()) }),
      )
      .optional(),
    truncated: z.boolean().optional(),
  })
  .passthrough();
const ringSchema = z
  .object({
    ring_id: z.string(),
    ring_score: z.number(),
    band: bandSchema.optional(),
    claims_count: z.number(),
    claimants_count: z.number(),
    shared: z
      .array(z.object({ type: z.string(), label: z.string(), count: z.number() }))
      .optional(),
    total_claimed_amount: z.number().optional(),
    first_seen: z.string().optional(),
    last_seen: z.string().optional(),
    status: z.string(),
    reasons: z.array(z.string()).optional(),
    data_source: z.string().optional(),
  })
  .passthrough();
export const ringListSchema = z
  .object({ items: z.array(ringSchema), total: z.number() })
  .passthrough();
export const ringDetailSchema = ringSchema
  .extend({
    claims: z.array(z.record(z.unknown())).optional(),
    timeline: z.array(z.object({ date: z.string(), event: z.string() })).optional(),
    graph: graphSchema.optional(),
    audit: z.array(z.record(z.unknown())).optional(),
  })
  .passthrough();
export const claimNetworkSchema = z
  .object({
    rings: z.array(z.record(z.unknown())).optional(),
    shared_identifiers: z.array(z.record(z.unknown())).optional(),
    evidence: z.array(z.record(z.unknown())).optional(),
  })
  .passthrough();
export const analyticsSummarySchema = z
  .object({
    claims_today: z.number(),
    fast_tracked: z.number(),
    flagged: z.number(),
    flagged_rate: z.number(),
    top_reasons: z
      .array(z.object({ id: z.string(), title: z.string(), count: z.number() }))
      .optional(),
    sparkline_7d: z.array(z.number()).optional(),
    open_rings: z.number().optional(),
  })
  .passthrough();
export const analyticsTrendsSchema = z
  .object({
    daily: z.array(
      z
        .object({
          date: z.string(),
          low: z.number(),
          medium: z.number(),
          high: z.number(),
          flagged_rate: z.number(),
          avg_risk: z.number(),
        })
        .passthrough(),
    ),
  })
  .passthrough();
export const transcribeSchema = z
  .object({
    language: z.string(),
    transcript: z.string().optional(),
    translation_en: z.string().optional(),
    extracted: z.record(z.unknown()).optional(),
  })
  .passthrough();
