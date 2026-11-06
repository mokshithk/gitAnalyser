import React, { useState } from 'react';

export default function MatchViewer({ matches }) {
  const [selectedMatchIndex, setSelectedMatchIndex] = useState(0);

  if (!matches || matches.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
        No similarity matches found above the similarity threshold.
      </div>
    );
  }

  const activeMatch = matches[selectedMatchIndex] || matches[0];
  const matchedPairs = activeMatch.details?.matched_pairs || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Target Selector Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
        {matches.map((m, idx) => {
          const isSelected = idx === selectedMatchIndex;
          const scorePercent = Math.round(m.score * 100);
          return (
            <button
              key={m.id || idx}
              onClick={() => setSelectedMatchIndex(idx)}
              className="btn btn-secondary"
              style={{
                background: isSelected ? '#1e293b' : '#0b1120',
                borderColor: isSelected ? '#0284c7' : '#334155',
                color: isSelected ? '#f8fafc' : '#94a3b8',
                fontSize: '0.8rem',
                whiteSpace: 'nowrap',
              }}
            >
              <span>{m.target_ref.split('/').pop() || m.target_ref}</span>
              <span className={`badge ${scorePercent >= 85 ? 'badge-high' : 'badge-medium'}`} style={{ fontSize: '0.65rem' }}>
                {scorePercent}%
              </span>
            </button>
          );
        })}
      </div>

      {/* Target Overview */}
      <div className="card-elevated" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Comparing against: </span>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
            {activeMatch.target_ref}
          </span>
          <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '0.5rem' }}>
            ({activeMatch.target_type})
          </span>
        </div>
        <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
          <strong>{matchedPairs.length}</strong> matched function pair(s)
        </div>
      </div>

      {/* Matched Pairs Side-by-Side Diff */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {matchedPairs.map((pair, pIdx) => {
          const simPct = Math.round((pair.similarity_score || 1.0) * 100);
          return (
            <div key={pIdx} className="card" style={{ padding: '1rem', background: '#0b1120', borderColor: '#334155' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid #1e293b', paddingBottom: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>
                    Pair #{pIdx + 1}:
                  </span>
                  <span className="font-mono" style={{ color: '#22c55e', fontSize: '0.8rem' }}>
                    {pair.source_function}()
                  </span>
                  <span style={{ color: '#64748b' }}>&harr;</span>
                  <span className="font-mono" style={{ color: '#38bdf8', fontSize: '0.8rem' }}>
                    {pair.target_function}()
                  </span>
                </div>

                <span className={`badge ${simPct >= 85 ? 'badge-high' : 'badge-medium'}`}>
                  {pair.match_type === 'exact_ast' ? '100% Exact AST Twin' : `${simPct}% Structural Match`}
                </span>
              </div>

              {/* Side-by-Side Code Boxes */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                {/* Source Column */}
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Source: {pair.source_file || 'unknown'}</span>
                    <span>Lines {pair.source_lines ? `${pair.source_lines[0]}-${pair.source_lines[1]}` : ''}</span>
                  </div>
                  <pre style={{
                    background: '#040813',
                    border: '1px solid #1e293b',
                    borderRadius: '0.375rem',
                    padding: '0.75rem',
                    fontSize: '0.75rem',
                    color: '#e2e8f0',
                    overflowX: 'auto',
                    maxHeight: '260px',
                    lineHeight: 1.4
                  }}>
                    <code>{pair.source_code}</code>
                  </pre>
                </div>

                {/* Target Column */}
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Target: {pair.target_file || 'unknown'}</span>
                    <span style={{ color: '#38bdf8' }}>Reference Repo</span>
                  </div>
                  <pre style={{
                    background: '#040813',
                    border: '1px solid #1e293b',
                    borderRadius: '0.375rem',
                    padding: '0.75rem',
                    fontSize: '0.75rem',
                    color: '#e2e8f0',
                    overflowX: 'auto',
                    maxHeight: '260px',
                    lineHeight: 1.4
                  }}>
                    <code>{pair.target_code}</code>
                  </pre>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
