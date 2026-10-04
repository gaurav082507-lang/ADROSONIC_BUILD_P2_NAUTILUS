import React, { useState } from 'react';
import { fetchClient } from '@/api/client';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, CheckCircle2, Loader2, FileText, Image as ImageIcon, Layers, Trash2 } from 'lucide-react';
import { ErrorBanner } from '@/components/ErrorBanner';

export default function AnalyzePage() {
  const [activeTab, setActiveTab] = useState('claim'); // 'image' | 'document' | 'claim'
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [completedSteps, setCompletedSteps] = useState([]);
  const [errorObj, setErrorObj] = useState(null);
  const navigate = useNavigate();

  // Single Image State
  const [singleImage, setSingleImage] = useState(null);

  // Single Document State
  const [singleDocument, setSingleDocument] = useState(null);

  // Claim Mode State
  const [claimImages, setClaimImages] = useState([]); // up to 6
  const [claimDocument, setClaimDocument] = useState(null);
  const [claimIdPhoto, setClaimIdPhoto] = useState(null);
  const [claimSelfie, setClaimSelfie] = useState(null);
  const [claimPolicyNumber, setClaimPolicyNumber] = useState('');
  const [claimAmount, setClaimAmount] = useState('');
  const [claimPeril, setClaimPeril] = useState('motor');

  const pollJob = async (jobId) => {
    setStatusText('Forensic processing initiated... tracking pipeline steps');
    for (let i = 0; i < 90; i++) {
      await new Promise(r => setTimeout(r, 600));
      const job = await fetchClient(`/jobs/${jobId}`);
      if (job.steps && job.steps.length > 0) {
        const finished = job.steps.filter(s => s.status === 'done').map(s => s.name);
        setCompletedSteps(finished);
        const running = job.steps.find(s => s.status === 'running');
        if (running) {
          setStatusText(`Executing: ${running.name}`);
        }
      }

      if (job.status === 'done' && job.result_id) {
        setStatusText('Analysis complete! Redirecting to forensic case report...');
        setTimeout(() => {
          navigate(`/app/results/${job.result_id}`);
        }, 350);
        return;
      } else if (job.status === 'failed') {
        throw new Error(job.error || 'Job failed during execution.');
      }
    }
    throw new Error('Analysis timed out after 54 seconds.');
  };

  const handleSingleImageSubmit = async (e) => {
    e.preventDefault();
    if (!singleImage) {
      setErrorObj({ code: 'NO_INPUT', message: 'Please select an image file to analyze.' });
      return;
    }
    setLoading(true);
    setErrorObj(null);
    setCompletedSteps([]);
    try {
      const formData = new FormData();
      formData.append('file', singleImage);
      const res = await fetchClient('/analyze/image', { method: 'POST', body: formData });
      if (res && res.job_id) {
        await pollJob(res.job_id);
      }
    } catch (err) {
      setErrorObj(err);
      setLoading(false);
    }
  };

  const handleSingleDocumentSubmit = async (e) => {
    e.preventDefault();
    if (!singleDocument) {
      setErrorObj({ code: 'NO_INPUT', message: 'Please select a document (PDF or image) to analyze.' });
      return;
    }
    setLoading(true);
    setErrorObj(null);
    setCompletedSteps([]);
    try {
      const formData = new FormData();
      formData.append('file', singleDocument);
      const res = await fetchClient('/analyze/document', { method: 'POST', body: formData });
      if (res && res.job_id) {
        await pollJob(res.job_id);
      }
    } catch (err) {
      setErrorObj(err);
      setLoading(false);
    }
  };

  const handleClaimSubmit = async (e) => {
    e.preventDefault();
    if (claimImages.length === 0 && !claimDocument && !claimIdPhoto && !claimSelfie) {
      setErrorObj({ code: 'NO_INPUT', message: 'Please upload at least one image or document for this claim.' });
      return;
    }
    if (claimImages.length > 6) {
      setErrorObj({ code: 'TOO_MANY_FILES', message: 'A maximum of 6 images is allowed per claim.' });
      return;
    }

    setLoading(true);
    setErrorObj(null);
    setCompletedSteps([]);
    try {
      const formData = new FormData();
      claimImages.forEach((img) => {
        formData.append('image', img);
      });
      if (claimDocument) formData.append('document', claimDocument);
      if (claimIdPhoto) formData.append('id_photo', claimIdPhoto);
      if (claimSelfie) formData.append('selfie', claimSelfie);

      // Metadata JSON
      const meta = {
        policy_number: claimPolicyNumber || undefined,
        claimed_amount: claimAmount ? parseFloat(claimAmount) : undefined,
        peril: claimPeril || undefined,
      };
      formData.append('metadata', JSON.stringify(meta));

      const res = await fetchClient('/analyze/claim', { method: 'POST', body: formData });
      if (res && res.job_id) {
        await pollJob(res.job_id);
      }
    } catch (err) {
      setErrorObj(err);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Forensic Intake & Analysis</h1>
        <p className="text-muted text-sm mt-1">
          Verify digital authenticity, inspect document tampering, and detect synthetic multi-modal insurance fraud.
        </p>
      </div>

      <ErrorBanner error={errorObj} onClose={() => setErrorObj(null)} />

      {/* Tabs */}
      <div className="flex border-b border-rule gap-2">
        <button
          onClick={() => { setActiveTab('claim'); setErrorObj(null); }}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'claim'
              ? 'border-marker text-ink font-semibold'
              : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          <Layers className="w-4 h-4" />
          Full Claim Package
        </button>
        <button
          onClick={() => { setActiveTab('image'); setErrorObj(null); }}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'image'
              ? 'border-marker text-ink font-semibold'
              : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          <ImageIcon className="w-4 h-4" />
          Single Image
        </button>
        <button
          onClick={() => { setActiveTab('document'); setErrorObj(null); }}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'document'
              ? 'border-marker text-ink font-semibold'
              : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          <FileText className="w-4 h-4" />
          Document / Invoice
        </button>
      </div>

      {/* Loading Progress State */}
      {loading ? (
        <div className="bg-surface p-8 rounded-xl border border-rule shadow-sm space-y-5 text-center">
          <Loader2 className="w-10 h-10 animate-spin text-marker mx-auto" />
          <div>
            <h3 className="text-lg font-bold text-ink">Analyzing Claim Artifacts</h3>
            <p className="text-sm text-muted mt-1">{statusText}</p>
          </div>
          {completedSteps.length > 0 && (
            <div className="max-w-md mx-auto text-left border border-rule rounded-lg p-3 bg-paper text-xs space-y-1.5 max-h-40 overflow-y-auto">
              {completedSteps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-2 text-green-700">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <>
          {/* TAB 1: FULL CLAIM */}
          {activeTab === 'claim' && (
            <form onSubmit={handleClaimSubmit} className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-6">
              <div>
                <h3 className="text-base font-semibold text-ink">1. Claim Evidence Files</h3>
                <p className="text-xs text-muted mt-0.5">Attach damage photos, repair estimates or hospital bills, and identity documents.</p>
              </div>

              {/* Photos Dropzone (0..6) */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-ink flex justify-between">
                  <span>Claim Damage Photos (0 to 6 images)</span>
                  <span className="text-muted">{claimImages.length}/6 selected</span>
                </label>
                <div className="border border-dashed border-rule rounded-lg p-4 bg-paper/50 flex flex-col items-center justify-center text-center">
                  <UploadCloud className="w-8 h-8 text-muted mb-2" />
                  <input
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp"
                    id="claim-images-input"
                    className="hidden"
                    onChange={(e) => {
                      const files = Array.from(e.target.files || []);
                      if (claimImages.length + files.length > 6) {
                        setErrorObj({ code: 'TOO_MANY_FILES', message: 'You can select up to 6 images in total.' });
                        return;
                      }
                      setClaimImages([...claimImages, ...files]);
                    }}
                  />
                  <label
                    htmlFor="claim-images-input"
                    className="cursor-pointer text-xs font-semibold px-3 py-1.5 rounded border border-rule bg-surface hover:bg-paper"
                  >
                    Select Images
                  </label>
                  <p className="text-[11px] text-muted mt-1.5">JPG, PNG, WebP up to 15 MB each</p>
                </div>

                {claimImages.length > 0 && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-2">
                    {claimImages.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 rounded border border-rule bg-paper text-xs">
                        <span className="truncate max-w-[120px]" title={file.name}>{file.name}</span>
                        <button
                          type="button"
                          onClick={() => setClaimImages(claimImages.filter((_, i) => i !== idx))}
                          className="text-red-500 hover:text-red-700 ml-2"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Document Dropzone (0..1) */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-ink">Bill / Estimate Document (0 or 1 PDF / image)</label>
                <div className="flex items-center gap-3">
                  <input
                    type="file"
                    accept="application/pdf,image/jpeg,image/png"
                    id="claim-doc-input"
                    className="hidden"
                    onChange={(e) => setClaimDocument(e.target.files?.[0] || null)}
                  />
                  <label
                    htmlFor="claim-doc-input"
                    className="cursor-pointer text-xs font-semibold px-3 py-1.5 rounded border border-rule bg-surface hover:bg-paper"
                  >
                    Choose Document
                  </label>
                  <span className="text-xs text-muted truncate">
                    {claimDocument ? claimDocument.name : 'No document selected'}
                  </span>
                  {claimDocument && (
                    <button
                      type="button"
                      onClick={() => setClaimDocument(null)}
                      className="text-xs text-red-500 hover:underline"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {/* Identity Documents */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-rule">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-ink">ID Document (Optional)</label>
                  <input
                    type="file"
                    accept="image/jpeg,image/png"
                    onChange={(e) => setClaimIdPhoto(e.target.files?.[0] || null)}
                    className="text-xs text-muted block w-full file:mr-2 file:py-1 file:px-2.5 file:rounded file:border file:border-rule file:text-xs file:bg-surface"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-ink">Selfie Photo (Optional)</label>
                  <input
                    type="file"
                    accept="image/jpeg,image/png"
                    onChange={(e) => setClaimSelfie(e.target.files?.[0] || null)}
                    className="text-xs text-muted block w-full file:mr-2 file:py-1 file:px-2.5 file:rounded file:border file:border-rule file:text-xs file:bg-surface"
                  />
                </div>
              </div>

              {/* Metadata Fields */}
              <div className="pt-2 border-t border-rule space-y-3">
                <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">Claim Metadata (Optional)</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-muted block mb-1">Policy Number</label>
                    <input
                      type="text"
                      placeholder="POL-2026-XXXX"
                      value={claimPolicyNumber}
                      onChange={(e) => setClaimPolicyNumber(e.target.value)}
                      className="w-full text-xs p-2 rounded border border-rule bg-paper"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted block mb-1">Claim Amount (₹)</label>
                    <input
                      type="number"
                      placeholder="25000"
                      value={claimAmount}
                      onChange={(e) => setClaimAmount(e.target.value)}
                      className="w-full text-xs p-2 rounded border border-rule bg-paper"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted block mb-1">Claim Peril</label>
                    <select
                      value={claimPeril}
                      onChange={(e) => setClaimPeril(e.target.value)}
                      className="w-full text-xs p-2 rounded border border-rule bg-paper"
                    >
                      <option value="motor">Motor Collision</option>
                      <option value="health">Health / Hospitalization</option>
                      <option value="property">Property Damage</option>
                    </select>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 rounded-lg bg-ink text-surface font-semibold text-sm hover:opacity-90 transition-opacity"
              >
                Analyze Claim Package
              </button>
            </form>
          )}

          {/* TAB 2: SINGLE IMAGE */}
          {activeTab === 'image' && (
            <form onSubmit={handleSingleImageSubmit} className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-6">
              <div className="border-2 border-dashed border-rule rounded-lg p-8 text-center bg-paper/50">
                <ImageIcon className="w-10 h-10 text-muted mx-auto mb-2" />
                <div className="text-sm font-medium text-ink mb-1">
                  {singleImage ? singleImage.name : 'Select a single image to test AI generation & ELA'}
                </div>
                <p className="text-xs text-muted mb-4">JPEG, PNG or WebP (up to 15 MB)</p>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  id="single-image-input"
                  className="hidden"
                  onChange={(e) => setSingleImage(e.target.files?.[0] || null)}
                />
                <label
                  htmlFor="single-image-input"
                  className="inline-flex cursor-pointer text-xs font-semibold px-3 py-1.5 rounded border border-rule bg-surface hover:bg-paper"
                >
                  Browse Image
                </label>
              </div>

              <button
                type="submit"
                disabled={!singleImage}
                className="w-full py-2.5 px-4 rounded-lg bg-ink text-surface font-semibold text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                Run Image Forensics
              </button>
            </form>
          )}

          {/* TAB 3: SINGLE DOCUMENT */}
          {activeTab === 'document' && (
            <form onSubmit={handleSingleDocumentSubmit} className="bg-surface p-6 rounded-xl border border-rule shadow-sm space-y-6">
              <div className="border-2 border-dashed border-rule rounded-lg p-8 text-center bg-paper/50">
                <FileText className="w-10 h-10 text-muted mx-auto mb-2" />
                <div className="text-sm font-medium text-ink mb-1">
                  {singleDocument ? singleDocument.name : 'Select a PDF invoice or scanned bill'}
                </div>
                <p className="text-xs text-muted mb-4">PDF, JPEG, or PNG (up to 10 pages, 15 MB)</p>
                <input
                  type="file"
                  accept="application/pdf,image/jpeg,image/png"
                  id="single-doc-input"
                  className="hidden"
                  onChange={(e) => setSingleDocument(e.target.files?.[0] || null)}
                />
                <label
                  htmlFor="single-doc-input"
                  className="inline-flex cursor-pointer text-xs font-semibold px-3 py-1.5 rounded border border-rule bg-surface hover:bg-paper"
                >
                  Browse Document
                </label>
              </div>

              <button
                type="submit"
                disabled={!singleDocument}
                className="w-full py-2.5 px-4 rounded-lg bg-ink text-surface font-semibold text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                Run Document Forensics
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
}
