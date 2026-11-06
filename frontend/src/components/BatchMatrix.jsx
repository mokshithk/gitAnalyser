import React from 'react';

export default function BatchMatrix({ projects, similarityMatrix }) {
  if (!projects || projects.length === 0 || !similarityMatrix) {
    return null;
  }

  function getScoreColor(score) {
    if (score >= 0.85) return 'rgba(239, 68, 68, 0.4)'; // high
    if (score >= 0.70) return 'rgba(245, 158, 11, 0.3)'; // medium
    if (score >= 0.40) return 'rgba(56, 189, 248, 0.2)'; // low
    return 'rgba(30, 41, 59, 0.5)'; // clean/none
  }

  return (
    <div className="card" style={{ marginTop: '1.5rem' }}>
      <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>
        Batch Pairwise Similarity Matrix
      </h3>
      <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>
        Structural AST cross-comparison across all repositories submitted in this batch.
      </p>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.8rem' }}>
          <thead>
            <tr>
              <th style={{ border: '1px solid #334155', padding: '0.5rem', background: '#0b1120', textAlign: 'left' }}>
                Project
              </th>
              {projects.map((p, idx) => (
                <th key={idx} style={{ border: '1px solid #334155', padding: '0.5rem', background: '#0b1120', textAlign: 'center' }}>
                  {p.name || `P#${idx + 1}`}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {projects.map((rowP, rIdx) => (
              <tr key={rIdx}>
                <td style={{ border: '1px solid #334155', padding: '0.5rem', background: '#0b1120', fontWeight: 600, color: '#e2e8f0' }}>
                  {rowP.name || `P#${rIdx + 1}`}
                </td>
                {projects.map((colP, cIdx) => {
                  const score = similarityMatrix[rIdx]?.[cIdx] ?? (rIdx === cIdx ? 1.0 : 0.0);
                  const isDiag = rIdx === cIdx;
                  return (
                    <td
                      key={cIdx}
                      style={{
                        border: '1px solid #334155',
                        padding: '0.5rem',
                        textAlign: 'center',
                        background: isDiag ? '#1e293b' : getScoreColor(score),
                        color: isDiag ? '#64748b' : score >= 0.70 ? '#fca5a5' : '#cbd5e1',
                        fontWeight: score >= 0.70 ? 700 : 400,
                        fontFamily: 'var(--font-mono)'
                      }}
                      title={`${rowP.name} vs ${colP.name}: ${Math.round(score * 100)}%`}
                    >
                      {Math.round(score * 100)}%
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
