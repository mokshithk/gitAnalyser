import React from 'react';

export default function DisclaimerBanner() {
  return (
    <div style={{
      background: 'rgba(239, 68, 68, 0.08)',
      border: '1px solid rgba(239, 68, 68, 0.25)',
      borderRadius: '0.5rem',
      padding: '0.875rem 1.25rem',
      marginBottom: '1.5rem',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.875rem'
    }}>
      <svg 
        style={{ width: '20px', height: '20px', color: '#f87171', flexShrink: 0, marginTop: '2px' }} 
        viewBox="0 0 24 24" 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="2" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      >
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <div>
        <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#fca5a5', marginBottom: '0.2rem' }}>
          Mandatory Human Review Disclaimer
        </h4>
        <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.45 }}>
          CodeProvenance produces explainable evidentiary signals for human review and academic triage only. 
          These metrics do <strong>NOT</strong> constitute proof of misconduct, plagiarism, or unauthorized collaboration. 
          Authentic engineering practices (e.g., squashed commits, offline drafting, library integration) naturally generate similar patterns.
        </p>
      </div>
    </div>
  );
}
