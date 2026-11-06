import React, { useState } from 'react';

const LIMITATIONS = [
  {
    title: "Thin or Squashed Git History",
    desc: "Repositories with few commits or squashed feature branches lack temporal resolution, obscuring incremental development."
  },
  {
    title: "No Git Metadata in Zip Uploads",
    desc: "Zip submissions without a .git folder run in similarity-only mode with zero commit telemetry or pacing data."
  },
  {
    title: "Reference Corpus Boundedness",
    desc: "Similarity scans compare against indexed reference repositories and peer projects in this system's database."
  },
  {
    title: "Timestamp Forgeability",
    desc: "Git timestamps can be manually overridden via environment variables (GIT_COMMITTER_DATE) or interactive rebase."
  },
  {
    title: "Language Support Scope",
    desc: "Structural AST fingerprinting normalizes Python syntax. Multi-language AST normalization is planned for future releases."
  }
];

export default function LimitationsPanel() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="card" style={{ marginTop: '1.5rem', background: '#131b2e' }}>
      <div 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          userSelect: 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <svg style={{ width: '18px', height: '18px', color: '#94a3b8' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#e2e8f0' }}>
            System Limitations & Boundary Conditions ({LIMITATIONS.length})
          </span>
        </div>
        <span style={{ fontSize: '0.8rem', color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
          {isOpen ? '[- Collapse]' : '[+ Expand]'}
        </span>
      </div>

      {isOpen && (
        <div style={{ marginTop: '1rem', borderTop: '1px solid #334155', paddingTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
          {LIMITATIONS.map((lim, idx) => (
            <div key={idx} style={{ background: '#0b1120', padding: '0.875rem', borderRadius: '0.375rem', border: '1px solid #1e293b' }}>
              <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#38bdf8', marginBottom: '0.25rem' }}>
                {lim.title}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4 }}>
                {lim.desc}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
