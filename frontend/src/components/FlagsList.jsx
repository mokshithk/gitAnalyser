import React, { useState } from 'react';

export default function FlagsList({ flags, onUpdateFlag }) {
  const [editingNotes, setEditingNotes] = useState({});
  const [savingId, setSavingId] = useState(null);

  if (!flags || flags.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '2rem', color: '#10b981' }}>
        <svg style={{ width: '32px', height: '32px', margin: '0 auto 0.5rem auto' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="m9 12 2 2 4-4" />
        </svg>
        <div style={{ fontWeight: 600 }}>No anomalous flags triggered.</div>
        <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Repository pacing and code similarity appear consistent.</div>
      </div>
    );
  }

  const handleStatusChange = async (flagId, newStatus) => {
    try {
      await onUpdateFlag(flagId, { review_status: newStatus });
    } catch (err) {
      alert('Failed to update status: ' + err.message);
    }
  };

  const handleSaveNote = async (flagId) => {
    setSavingId(flagId);
    try {
      await onUpdateFlag(flagId, { note: editingNotes[flagId] || '' });
    } catch (err) {
      alert('Failed to save note: ' + err.message);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {flags.map((flag) => {
        const ev = flag.evidence || {};
        const questions = ev.questions || [];
        const isHigh = flag.severity === 'high';
        const isMed = flag.severity === 'medium';
        const badgeClass = isHigh ? 'badge-high' : isMed ? 'badge-medium' : 'badge-low';

        return (
          <div 
            key={flag.id} 
            className="card"
            style={{
              borderColor: isHigh ? 'rgba(239, 68, 68, 0.4)' : isMed ? 'rgba(245, 158, 11, 0.3)' : '#334155',
              background: '#0e1726'
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span className={`badge ${badgeClass}`}>
                  {flag.severity}
                </span>
                <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#f8fafc' }}>
                  {flag.title}
                </span>
              </div>

              {/* Status Selector */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Review:</span>
                <select
                  value={flag.review_status}
                  onChange={(e) => handleStatusChange(flag.id, e.target.value)}
                  style={{
                    background: '#1e293b',
                    color: flag.review_status === 'reviewed' ? '#4ade80' : flag.review_status === 'dismissed' ? '#94a3b8' : '#f87171',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    padding: '0.2rem 0.5rem',
                    fontSize: '0.75rem',
                    fontWeight: 600
                  }}
                >
                  <option value="open">OPEN (Needs Review)</option>
                  <option value="reviewed">REVIEWED (Verified)</option>
                  <option value="dismissed">DISMISSED (False Alarm)</option>
                </select>
              </div>
            </div>

            {/* Evidence Body */}
            <div style={{ marginTop: '0.75rem', fontSize: '0.825rem', color: '#cbd5e1', lineHeight: 1.5 }}>
              {ev.description && <p style={{ marginBottom: '0.4rem' }}>{ev.description}</p>}
              {ev.commits && ev.commits.length > 0 && (
                <div style={{ marginTop: '0.5rem', marginBottom: '0.6rem', background: '#0b1120', padding: '0.6rem', borderRadius: '4px', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem' }}>
                    Burst Commits in Window ({ev.commits.length}):
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {ev.commits.map((c, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                        <span style={{ color: '#38bdf8' }}>{c.sha}</span>
                        <span style={{ color: '#4ade80' }}>+{c.lines} lines</span>
                        <span style={{ color: '#94a3b8' }}>within {c.seconds}s</span>
                        {c.share_percentage ? <span style={{ color: '#f59e0b' }}>({c.share_percentage}% of final)</span> : null}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {ev.corroborating_signals && ev.corroborating_signals.length > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.4rem' }}>
                  <span style={{ color: '#94a3b8' }}>Corroborated by:</span>
                  <span style={{ color: '#ef4444', fontWeight: 600 }}>{ev.corroborating_signals.join(', ')}</span>
                </div>
              )}
              {ev.sha && (
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.4rem' }}>
                  <span style={{ color: '#94a3b8' }}>Commit SHA:</span>
                  <span className="font-mono" style={{ color: '#38bdf8' }}>{ev.sha}</span>
                </div>
              )}
              {ev.share_percentage && (
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.4rem' }}>
                  <span style={{ color: '#94a3b8' }}>Codebase Fraction:</span>
                  <span style={{ color: '#f59e0b', fontWeight: 600 }}>{ev.share_percentage}% of total code</span>
                </div>
              )}
              {ev.target_ref && (
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.4rem' }}>
                  <span style={{ color: '#94a3b8' }}>Matched Target:</span>
                  <span className="font-mono" style={{ color: '#38bdf8' }}>{ev.target_ref}</span>
                </div>
              )}
            </div>

            {/* Suggested Interview Questions */}
            {questions.length > 0 && (
              <div style={{ marginTop: '0.75rem', background: '#0b1120', padding: '0.75rem', borderRadius: '0.375rem', border: '1px solid #1e293b' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#38bdf8', marginBottom: '0.4rem' }}>
                  Suggested Follow-up Questions for Viva / Review:
                </div>
                <ul style={{ paddingLeft: '1.2rem', margin: 0 }}>
                  {questions.map((q, qIdx) => (
                    <li key={qIdx} style={{ fontSize: '0.8rem', color: '#e2e8f0', marginBottom: '0.25rem' }}>
                      {q}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Reviewer Note */}
            <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                placeholder={flag.note ? `Note: ${flag.note}` : "Add an instructor/reviewer note..."}
                defaultValue={flag.note || ''}
                onChange={(e) => setEditingNotes({ ...editingNotes, [flag.id]: e.target.value })}
                className="form-input"
                style={{ padding: '0.35rem 0.6rem', fontSize: '0.8rem', flex: 1 }}
              />
              <button
                onClick={() => handleSaveNote(flag.id)}
                disabled={savingId === flag.id}
                className="btn btn-secondary"
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
              >
                {savingId === flag.id ? 'Saving...' : 'Save Note'}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
