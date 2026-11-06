import React from 'react';

export default function CommitTimeline({ commits, bursts, largeShareCommits }) {
  if (!commits || commits.length === 0) {
    return <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No commit history available.</div>;
  }

  // Find max lines changed for relative sizing
  const maxLines = Math.max(...commits.map(c => (c.lines_added + c.lines_deleted)), 1);

  const burstShas = new Set((bursts || []).map(b => b.sha));
  const largeShareShas = new Set((largeShareCommits || []).map(l => l.sha));

  return (
    <div style={{ position: 'relative', paddingLeft: '1.5rem', borderLeft: '2px solid #334155' }}>
      {commits.map((c, idx) => {
        const totalLines = c.lines_added + c.lines_deleted;
        const normalizedSize = Math.max(12, Math.min(32, Math.round(12 + (totalLines / maxLines) * 20)));
        const shortSha = c.sha.substring(0, 7);
        const isBurst = burstShas.has(shortSha);
        const isLargeShare = largeShareShas.has(shortSha);

        let bubbleColor = '#38bdf8';
        if (isLargeShare || isBurst) bubbleColor = '#ef4444';
        else if (totalLines > 200) bubbleColor = '#f59e0b';

        return (
          <div key={c.sha || idx} style={{ marginBottom: '1.25rem', position: 'relative' }}>
            {/* Sized Timeline Node */}
            <div 
              style={{
                position: 'absolute',
                left: `-${normalizedSize / 2 + 25}px`,
                top: '4px',
                width: `${normalizedSize}px`,
                height: `${normalizedSize}px`,
                borderRadius: '50%',
                background: bubbleColor,
                border: '2px solid #0f172a',
                boxShadow: `0 0 10px ${bubbleColor}40`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.6rem',
                color: '#0f172a',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
              title={`Commit ${shortSha}: ${totalLines} lines changed`}
            />

            <div style={{
              background: '#0b1120',
              border: isBurst || isLargeShare ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid #1e293b',
              borderRadius: '0.375rem',
              padding: '0.75rem 1rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="font-mono" style={{ background: '#1e293b', color: '#38bdf8', fontSize: '0.75rem', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>
                    {shortSha}
                  </span>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc' }}>
                    {c.author_name}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    &lt;{c.author_email}&gt;
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontSize: '0.75rem', color: '#22c55e', fontFamily: 'var(--font-mono)' }}>
                    +{c.lines_added}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#ef4444', fontFamily: 'var(--font-mono)' }}>
                    -{c.lines_deleted}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {new Date(c.commit_date).toLocaleString()}
                  </span>
                </div>
              </div>

              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.25rem' }}>
                {c.message}
              </div>

              {(isBurst || isLargeShare) && (
                <div style={{ marginTop: '0.4rem', display: 'flex', gap: '0.5rem' }}>
                  {isBurst && (
                    <span className="badge badge-high" style={{ fontSize: '0.65rem' }}>
                      Pace Burst
                    </span>
                  )}
                  {isLargeShare && (
                    <span className="badge badge-high" style={{ fontSize: '0.65rem' }}>
                      Large Codebase Share
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
