import React, { useState, useEffect } from 'react';
import { api } from '../api';

export default function DashboardPage({ onSelectAnalysis, onNewAnalysis }) {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [statusFilter, setStatusFilter] = useState('');
  const [modeFilter, setModeFilter] = useState('');
  const [search, setSearch] = useState('');

  const loadData = async () => {
    try {
      const data = await api.listAnalyses({
        status: statusFilter,
        mode: modeFilter,
        search: search.trim(),
      });
      setAnalyses(data);
    } catch (err) {
      setError(err.message || 'Failed to load analyses');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Poll every 5s if any analysis is pending or active
    const interval = setInterval(() => {
      loadData();
    }, 5000);
    return () => clearInterval(interval);
  }, [statusFilter, modeFilter, search]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm(`Delete analysis #${id}?`)) return;
    try {
      await api.deleteAnalysis(id);
      setAnalyses(analyses.filter(a => a.id !== id));
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  const getPriorityBadge = (a) => {
    if (a.status === 'failed') {
      return <span className="badge badge-neutral">NOT ANALYZED</span>;
    }
    const priority = a.options?.review_priority || (a.status === 'done' ? 'CLEAN' : 'PENDING');
    const classes = {
      HIGH: 'badge-high',
      MEDIUM: 'badge-medium',
      LOW: 'badge-low',
      CLEAN: 'badge-clean',
      PENDING: 'badge-low',
    };
    return <span className={`badge ${classes[priority] || 'badge-neutral'}`}>{priority}</span>;
  };

  const getStatusBadge = (status) => {
    const isRunning = ['queued', 'cloning', 'parsing', 'comparing'].includes(status);
    return (
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.4rem',
        fontSize: '0.75rem',
        fontFamily: 'var(--font-mono)',
        color: status === 'done' ? '#4ade80' : status === 'failed' ? '#f87171' : '#38bdf8'
      }}>
        {isRunning && (
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: '#38bdf8',
            animation: 'pulse 1.5s infinite'
          }}></span>
        )}
        {status.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="container" style={{ padding: '2rem 1.5rem' }}>
      {/* Top Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Analysis Dashboard
          </h1>
          <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '0.2rem' }}>
            Review triage priorities, commit pacing telemetry, and structural code similarity.
          </p>
        </div>

        <button onClick={onNewAnalysis} className="btn btn-primary">
          + Start New Analysis
        </button>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem', background: '#1e293b' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: 1, minWidth: '220px' }}>
            <input
              type="text"
              placeholder="Search repository URL or archive..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="form-input"
            />
          </div>

          <div style={{ minWidth: '150px' }}>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="form-input"
            >
              <option value="">All Statuses</option>
              <option value="done">Done</option>
              <option value="cloning">Cloning</option>
              <option value="parsing">Parsing</option>
              <option value="comparing">Comparing</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div style={{ minWidth: '150px' }}>
            <select
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
              className="form-input"
            >
              <option value="">All Modes</option>
              <option value="full">Full (Git History)</option>
              <option value="similarity_only">Similarity Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Analyses Table */}
      {loading && analyses.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
          Loading analyses...
        </div>
      ) : analyses.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '0.5rem' }}>
            No analyses submitted yet
          </div>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '1.25rem' }}>
            Submit a public or private Git URL or upload a zip archive to triage code provenance.
          </p>
          <button onClick={onNewAnalysis} className="btn btn-primary">
            Submit First Repository
          </button>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: '#0b1120', borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                  <th style={{ padding: '0.875rem 1.25rem' }}>Source / Repository</th>
                  <th style={{ padding: '0.875rem 1rem' }}>Type & Mode</th>
                  <th style={{ padding: '0.875rem 1rem' }}>Review Priority</th>
                  <th style={{ padding: '0.875rem 1rem' }}>Status</th>
                  <th style={{ padding: '0.875rem 1rem' }}>Date</th>
                  <th style={{ padding: '0.875rem 1.25rem', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((a) => (
                  <tr
                    key={a.id}
                    onClick={() => onSelectAnalysis(a.id)}
                    style={{
                      borderBottom: '1px solid #1e293b',
                      cursor: 'pointer',
                      transition: 'background 120ms ease'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#1a2234')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '1rem 1.25rem', maxWidth: '300px' }}>
                      <div style={{ fontWeight: 600, color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {a.source}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                        Analysis #{a.id}
                      </div>
                    </td>

                    <td style={{ padding: '1rem' }}>
                      <div style={{ textTransform: 'uppercase', fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 600 }}>
                        {a.input_type}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: a.status === 'failed' ? '#64748b' : a.mode === 'full' ? '#38bdf8' : '#f59e0b' }}>
                        {a.status === 'failed' ? 'Failed Ingestion' : (a.mode === 'full' ? 'Full History' : 'Similarity Only')}
                      </div>
                    </td>

                    <td style={{ padding: '1rem' }}>
                      {getPriorityBadge(a)}
                    </td>

                    <td style={{ padding: '1rem' }}>
                      {getStatusBadge(a.status)}
                    </td>

                    <td style={{ padding: '1rem', color: '#94a3b8', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>

                    <td style={{ padding: '1rem 1.25rem', textAlign: 'right' }}>
                      <button
                        onClick={(e) => handleDelete(e, a.id)}
                        className="btn btn-secondary"
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem', color: '#f87171' }}
                        title="Delete analysis"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
