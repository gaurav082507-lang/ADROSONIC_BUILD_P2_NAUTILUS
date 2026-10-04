import { fetchClient } from './client';

export async function loginApi(email, password) {
  return fetchClient('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  });
}

export async function getMeApi() {
  return fetchClient('/auth/me');
}

export async function getPoliciesApi() {
  return fetchClient('/policies/mine');
}

export async function createClaimApi(formData) {
  return fetchClient('/claims', { method: 'POST', body: formData });
}

export async function getMyClaimsApi() {
  return fetchClient('/claims/mine');
}

export async function getClaimStatusApi(id) {
  return fetchClient(`/claims/${id}/status`);
}

export async function getClaimEvidenceTimelineApi(id) {
  return fetchClient(`/claims/${id}/evidence-timeline`);
}

export async function getQueueApi() {
  return fetchClient('/queue');
}

export async function postDecisionDraftApi(resultId, body) {
  return fetchClient(`/results/${resultId}/decision/draft`, { method: 'POST', body: JSON.stringify(body) });
}

export async function postDecisionApi(resultId, body) {
  return fetchClient(`/results/${resultId}/decision`, { method: 'POST', body: JSON.stringify(body) });
}

export async function startLivenessSessionApi() {
  return fetchClient('/identity/liveness/session', { method: 'POST' });
}

export async function verifyLivenessApi(formData) {
  return fetchClient('/identity/liveness/verify', { method: 'POST', body: formData });
}
