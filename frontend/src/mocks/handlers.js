export async function handleMock(endpoint, _options) {
  // Simulate delay
  await new Promise(r => setTimeout(r, 500));

  if (endpoint.startsWith('/analyze')) {
    return { job_id: 'mock-job-123' };
  }

  if (endpoint.startsWith('/jobs')) {
    return {
      job_id: 'mock-job-123',
      status: 'done',
      mode: 'claim',
      steps: [],
      result_id: 'mock-result-HIGH'
    };
  }

  if (endpoint.startsWith('/results')) {
    return {
      id: 'mock-result-HIGH',
      overall: {
        risk: 0.95,
        band: 'HIGH',
        confidence: 'high',
        summary: 'Mocked high fraud.'
      },
      evidence: []
    };
  }

  throw new Error(`Mock not implemented for ${endpoint}`);
}
