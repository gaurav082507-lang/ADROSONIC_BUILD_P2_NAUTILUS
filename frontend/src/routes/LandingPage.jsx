import React from 'react';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  return (
    <div className="p-8 text-center min-h-screen flex flex-col items-center justify-center bg-paper text-ink">
      <h1 className="text-4xl font-bold mb-4">Lucen AI</h1>
      <p className="mb-8">Catch AI-faked claims before they're paid.</p>
      <div className="flex justify-center gap-4">
        <Link to="/claim/new" className="bg-ink text-white px-4 py-2 rounded">File a claim</Link>
        <Link to="/login" className="border border-rule bg-surface px-4 py-2 rounded">Investigator Demo</Link>
      </div>
    </div>
  );
}
