import React from 'react';
import { AlertCircle, XCircle } from 'lucide-react';

const ERROR_MESSAGES = {
  UNSUPPORTED_FILE_TYPE: 'Only JPG, PNG, WebP, and PDF files are supported.',
  FILE_TOO_LARGE: 'The selected file exceeds the 15 MB limit.',
  TOO_MANY_PAGES: 'PDF exceeds maximum allowed page count (10 pages).',
  TOO_MANY_FILES: 'Maximum of 6 photos per claim allowed.',
  CORRUPT_FILE: 'File is corrupted, unreadable, or exceeds safe dimensions.',
  NO_INPUT: 'Please select at least one file to analyze.',
  RATE_LIMITED: 'Rate limit exceeded (max 20 requests/minute). Please slow down and wait a few seconds.',
  JOB_NOT_FOUND: 'The requested job was not found.',
  RESULT_NOT_FOUND: 'The requested analysis result does not exist or has been deleted.',
  VALIDATION_ERROR: 'Request validation failed. Please check your inputs.',
  INTERNAL_ERROR: 'An internal server error occurred. Please try again.',
};

export function ErrorBanner({ error, onClose }) {
  if (!error) return null;

  const code = typeof error === 'object' ? error.error_code || error.code : null;
  const rawMsg = typeof error === 'object' ? error.message : String(error);
  const friendlyMsg = (code && ERROR_MESSAGES[code]) || rawMsg || 'An error occurred.';

  return (
    <div className="p-3.5 rounded-lg border border-red-200 bg-red-50 text-red-800 text-sm flex items-start justify-between gap-3 shadow-sm">
      <div className="flex items-start gap-2.5">
        <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
        <div>
          <div className="font-semibold text-red-900">{code || 'Error'}</div>
          <div className="text-red-700 mt-0.5">{friendlyMsg}</div>
        </div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-red-500 hover:text-red-700 transition-colors p-1"
          aria-label="Dismiss error"
        >
          <XCircle className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
