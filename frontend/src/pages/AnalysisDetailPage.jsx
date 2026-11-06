import React, { useState, useEffect } from 'react';
import { api } from '../api';
import DisclaimerBanner from '../components/DisclaimerBanner';
import LimitationsPanel from '../components/LimitationsPanel';
import CommitTimeline from '../components/CommitTimeline';
import ActivityHeatmap from '../components/ActivityHeatmap';
import CodeGrowthChart from '../components/CodeGrowthChart';
import FlagsList from '../components/FlagsList';
import MatchViewer from '../components/MatchViewer';

export default function AnalysisDetailPage({ analysisId, onBack }) {
  const [analysis, setAnalysis] = useState(null);
  const [commits, setCommits] = useState([]);
  const [flags, setFlags] = useState([]);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('flags'); // 'flags', 'timeline', 'growth', 'similarity', 'commits'
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const fetchAnalysisData = async () => {
    try {
      const a = await api.getAnalysis(analysisId);
      setAnalysis(a);

      if (a.status === 'done') {
        const [commRes, flgRes, matchRes] = await Promise.all([
          api.getCommits(analysisId, 200),
          api.getFlags(analysisId),
          api.getMatches(analysisId),
        ]);
        setCommits(commRes);
        setFlags(flgRes);
        setMatches(matchRes);
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch analysis details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalysisData();
    // Poll every 3 seconds if status is running
    const interval = setInterval(() => {
      if (analysis && ['queued', 'cloning', 'parsing', 'comparing'].includes(analysis.status)) {
        fetchAnalysisData();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [analysisId, analysis?.status]);

  const handleUpdateFlag = async (flagId, payload) => {
    const updated = await api.updateFlag(analysisId, flagId, payload);
    setFlags(flags.map(f => f.id === flagId ? updated : f));
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      await api.downloadPdf(analysisId);
    } catch (err) {
      alert('Failed to generate PDF report: ' + err.message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  if (loading && !analysis) {
    return (
      <div className="container" style={{ padding: '3rem 1.5rem', textAlign: 'center', color: '#94a3b8' }}>
        Loading analysis #{analysisId}...
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="container" style={{ padding: '3rem 1.5rem' }}>
        <button onClick={onBack} className="btn btn-secondary" style={{ marginBottom: '1rem' }}>
          &larr; Back to Dashboard
        </button>
        <div className="card" style={{ color: '#f87171' }}>
          Error: {error || 'Analysis not found'}
        </div>
      </div>
    );
  }

  const opts = analysis.options || {};
  const commitMetrics = opts.commit_metrics || {};
  const priority = opts.review_priority || 'CLEAN';
  const isRunning = ['queued', 'cloning', 'parsing', 'comparing'].includes(analysis.status);

  const priorityColors = {
    HIGH: 'badge-high',
    MEDIUM: 'badge-medium',
    LOW: 'badge-low',
    CLEAN: 'badge-clean',
  };

  return (
    <div className="container" style={{ padding: '2rem 1.5rem' }}>
      {/* Back & PDF Actions Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
        <button onClick={onBack} className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
          &larr; Back to Dashboard
        </button>

        {analysis.status === 'done' && (
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="btn btn-secondary"
            style={{ borderColor: '#0284c7', color: '#38bdf8' }}
          >
            <svg style={{ width: '16px', height: '16px' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            {downloadingPdf ? 'Generating PDF...' : 'Download PDF Triage Report'}
          </button>
        )}
      </div>

      {/* Main Title Banner */}
      <div className="card" style={{ marginBottom: '1.5rem', background: '#1e293b' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
              <span className={`badge ${priorityColors[priority] || 'badge-low'}`}>
                {priority} PRIORITY
              </span>
              <span className="badge badge-low" style={{ background: '#0b1120' }}>
                {analysis.mode === 'full' ? 'Full History Mode' : 'Similarity Only Mode'}
              </span>
              <span style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                ID #{analysis.id}
              </span>
            </div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', wordBreak: 'break-all' }}>
              {analysis.source}
            </h1>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Analysis Pipeline Status</div>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontWeight: 600,
              fontSize: '0.9rem',
              color: analysis.status === 'done' ? '#4ade80' : analysis.status === 'failed' ? '#f87171' : '#38bdf8'
            }}>
              {isRunning && <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#38bdf8', animation: 'pulse 1s infinite' }}></span>}
              {analysis.status.toUpperCase()}
            </div>
          </div>
        </div>

        {/* Stepper Progress Bar */}
        {isRunning && (
          <div style={{ marginTop: '1.5rem', borderTop: '1px solid #334155', paddingTop: '1rem' }}>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
              Running pipeline stages...
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
              {['cloning', 'parsing', 'comparing', 'done'].map((stage, sIdx) => {
                const stages = ['queued', 'cloning', 'parsing', 'comparing', 'done'];
                const currentIdx = stages.indexOf(analysis.status);
                const thisIdx = stages.indexOf(stage);
                const isPassed = currentIdx >= thisIdx;
                return (
                  <div key={stage} style={{
                    padding: '0.5rem',
                    background: isPassed ? 'rgba(56, 189, 248, 0.15)' : '#0b1120',
                    border: isPassed ? '1px solid #38bdf8' : '1px solid #1e293b',
                    borderRadius: '4px',
                    textAlign: 'center',
                    fontSize: '0.75rem',
                    color: isPassed ? '#38bdf8' : '#64748b',
                    fontWeight: 600
                  }}>
                    {stage.toUpperCase()}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {analysis.status === 'failed' && (
          <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '4px', color: '#f87171', fontSize: '0.85rem' }}>
            <strong>Analysis Failed:</strong> {analysis.error_message}
          </div>
        )}
      </div>

      {/* Mandatory Human Review Disclaimer */}
      <DisclaimerBanner />

      {/* Quick Telemetry Cards */}
      {analysis.status === 'done' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          <div className="card-elevated">
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Total Commits</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
              {commitMetrics.total_commits || (analysis.mode === 'full' ? commits.length : 'N/A')}
            </div>
          </div>

          <div className="card-elevated">
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Final Net Lines</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#22c55e', fontFamily: 'var(--font-mono)' }}>
              {commitMetrics.final_codebase_lines || 'N/A'}
            </div>
          </div>

          <div className="card-elevated">
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Flags Triggered</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: flags.length > 0 ? '#f59e0b' : '#10b981', fontFamily: 'var(--font-mono)' }}>
              {flags.length}
            </div>
          </div>

          <div className="card-elevated">
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Similarity Matches</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: matches.length > 0 ? '#38bdf8' : '#64748b', fontFamily: 'var(--font-mono)' }}>
              {matches.length}
            </div>
          </div>
        </div>
      )}

      {/* View Tabs */}
      {analysis.status === 'done' && (
        <div>
          <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.5rem', marginBottom: '1.5rem', overflowX: 'auto' }}>
            <button
              onClick={() => setActiveTab('flags')}
              className="btn btn-secondary"
              style={{
                background: activeTab === 'flags' ? '#1e293b' : 'transparent',
                borderColor: activeTab === 'flags' ? '#0284c7' : 'transparent',
                color: activeTab === 'flags' ? '#f8fafc' : '#94a3b8'
              }}
            >
              Flags & Viva Questions ({flags.length})
            </button>

            {analysis.mode === 'full' && (
              <>
                <button
                  onClick={() => setActiveTab('timeline')}
                  className="btn btn-secondary"
                  style={{
                    background: activeTab === 'timeline' ? '#1e293b' : 'transparent',
                    borderColor: activeTab === 'timeline' ? '#0284c7' : 'transparent',
                    color: activeTab === 'timeline' ? '#f8fafc' : '#94a3b8'
                  }}
                >
                  Timeline & Heatmap
                </button>

                <button
                  onClick={() => setActiveTab('growth')}
                  className="btn btn-secondary"
                  style={{
                    background: activeTab === 'growth' ? '#1e293b' : 'transparent',
                    borderColor: activeTab === 'growth' ? '#0284c7' : 'transparent',
                    color: activeTab === 'growth' ? '#f8fafc' : '#94a3b8'
                  }}
                >
                  Code Growth Curve
                </button>
              </>
            )}

            <button
              onClick={() => setActiveTab('similarity')}
              className="btn btn-secondary"
              style={{
                background: activeTab === 'similarity' ? '#1e293b' : 'transparent',
                borderColor: activeTab === 'similarity' ? '#0284c7' : 'transparent',
                color: activeTab === 'similarity' ? '#f8fafc' : '#94a3b8'
              }}
            >
              AST Similarity & Match Viewer ({matches.length})
            </button>

            {analysis.mode === 'full' && (
              <button
                onClick={() => setActiveTab('commits')}
                className="btn btn-secondary"
                style={{
                  background: activeTab === 'commits' ? '#1e293b' : 'transparent',
                  borderColor: activeTab === 'commits' ? '#0284c7' : 'transparent',
                  color: activeTab === 'commits' ? '#f8fafc' : '#94a3b8'
                }}
              >
                Raw Commits ({commits.length})
              </button>
            )}
          </div>

          {/* Tab Panes */}
          {activeTab === 'flags' && (
            <FlagsList flags={flags} onUpdateFlag={handleUpdateFlag} />
          )}

          {activeTab === 'timeline' && analysis.mode === 'full' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              <div className="card">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>
                  24-Hour x 7-Day Activity Heatmap
                </h3>
                <ActivityHeatmap matrix={commitMetrics.heatmap} />
              </div>

              <div className="card">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '1rem' }}>
                  Chronological Commit Timeline (Bubble size = Diff Volume)
                </h3>
                <CommitTimeline 
                  commits={commits} 
                  bursts={commitMetrics.bursts} 
                  largeShareCommits={commitMetrics.large_share_commits} 
                />
              </div>
            </div>
          )}

          {activeTab === 'growth' && analysis.mode === 'full' && (
            <div className="card">
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '1rem' }}>
                Cumulative Codebase Growth Timeline
              </h3>
              <CodeGrowthChart timeline={commitMetrics.growth_timeline} />
            </div>
          )}

          {activeTab === 'similarity' && (
            <MatchViewer matches={matches} />
          )}

          {activeTab === 'commits' && analysis.mode === 'full' && (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
                  <thead>
                    <tr style={{ background: '#0b1120', borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                      <th style={{ padding: '0.6rem 1rem' }}>SHA</th>
                      <th style={{ padding: '0.6rem 1rem' }}>Author</th>
                      <th style={{ padding: '0.6rem 1rem' }}>Date</th>
                      <th style={{ padding: '0.6rem 1rem' }}>Changes</th>
                      <th style={{ padding: '0.6rem 1rem' }}>Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commits.map((c) => (
                      <tr key={c.sha} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td className="font-mono" style={{ padding: '0.6rem 1rem', color: '#38bdf8' }}>{c.sha.substring(0, 7)}</td>
                        <td style={{ padding: '0.6rem 1rem', color: '#f8fafc' }}>{c.author_name}</td>
                        <td style={{ padding: '0.6rem 1rem', color: '#94a3b8' }}>{new Date(c.commit_date).toLocaleString()}</td>
                        <td className="font-mono" style={{ padding: '0.6rem 1rem' }}>
                          <span style={{ color: '#22c55e' }}>+{c.lines_added}</span>{' '}
                          <span style={{ color: '#ef4444' }}>-{c.lines_deleted}</span>
                        </td>
                        <td style={{ padding: '0.6rem 1rem', color: '#cbd5e1' }}>{c.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Limitations Panel */}
      <LimitationsPanel />
    </div>
  );
}
