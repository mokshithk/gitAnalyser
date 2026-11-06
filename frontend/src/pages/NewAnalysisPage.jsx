import React, { useState } from 'react';
import { api } from '../api';

export default function NewAnalysisPage({ onAnalysisCreated, onCancel }) {
  const [activeTab, setActiveTab] = useState('url'); // 'url', 'zip', 'batch'
  
  // URL Form State
  const [repoUrl, setRepoUrl] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [starterRepoUrl, setStarterRepoUrl] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Zip Form State
  const [zipFile, setZipFile] = useState(null);
  const [zipStarterUrl, setZipStarterUrl] = useState('');

  // Batch Form State
  const [batchUrls, setBatchUrls] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmitUrl = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const payload = {
        repo_url: repoUrl.trim(),
        access_token: accessToken.trim() || null,
        starter_repo_url: starterRepoUrl.trim() || null,
        start_date: startDate ? new Date(startDate).toISOString() : null,
        end_date: endDate ? new Date(endDate).toISOString() : null,
      };
      const res = await api.submitGitUrl(payload);
      onAnalysisCreated(res.id);
    } catch (err) {
      setError(err.message || 'Failed to submit Git URL');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitZip = async (e) => {
    e.preventDefault();
    if (!zipFile) {
      setError('Please select a .zip archive');
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const res = await api.submitZip(zipFile, zipStarterUrl.trim() || null);
      onAnalysisCreated(res.id);
    } catch (err) {
      setError(err.message || 'Failed to submit zip file');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitBatch = async (e) => {
    e.preventDefault();
    const urls = batchUrls.split('\n').map(u => u.trim()).filter(Boolean);
    if (urls.length < 2) {
      setError('Batch mode requires at least 2 repository URLs');
      return;
    }
    setError(null);
    setLoading(true);

    try {
      // Submit each URL and navigate to the first created one
      let firstId = null;
      for (const url of urls) {
        const res = await api.submitGitUrl({ repo_url: url });
        if (!firstId) firstId = res.id;
      }
      onAnalysisCreated(firstId);
    } catch (err) {
      setError(err.message || 'Failed to submit batch');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: '780px', padding: '2rem 1.5rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <button onClick={onCancel} className="btn btn-secondary" style={{ marginBottom: '1rem', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}>
          &larr; Back to Dashboard
        </button>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.02em' }}>
          Submit Repository for Triage Analysis
        </h1>
        <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '0.2rem' }}>
          Choose Git URL, Zip archive, or Batch mode to inspect commit history and AST similarity.
        </p>
      </div>

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: '0.375rem',
          padding: '0.875rem',
          color: '#f87171',
          fontSize: '0.85rem',
          marginBottom: '1.5rem'
        }}>
          {error}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.5rem' }}>
        <button
          onClick={() => { setActiveTab('url'); setError(null); }}
          className="btn btn-secondary"
          style={{
            background: activeTab === 'url' ? '#1e293b' : 'transparent',
            borderColor: activeTab === 'url' ? '#0284c7' : 'transparent',
            color: activeTab === 'url' ? '#f8fafc' : '#94a3b8'
          }}
        >
          Git Repository URL
        </button>

        <button
          onClick={() => { setActiveTab('zip'); setError(null); }}
          className="btn btn-secondary"
          style={{
            background: activeTab === 'zip' ? '#1e293b' : 'transparent',
            borderColor: activeTab === 'zip' ? '#0284c7' : 'transparent',
            color: activeTab === 'zip' ? '#f8fafc' : '#94a3b8'
          }}
        >
          Zip Archive Upload
        </button>

        <button
          onClick={() => { setActiveTab('batch'); setError(null); }}
          className="btn btn-secondary"
          style={{
            background: activeTab === 'batch' ? '#1e293b' : 'transparent',
            borderColor: activeTab === 'batch' ? '#0284c7' : 'transparent',
            color: activeTab === 'batch' ? '#f8fafc' : '#94a3b8'
          }}
        >
          Batch Submissions
        </button>
      </div>

      {/* Form Content */}
      <div className="card">
        {activeTab === 'url' && (
          <form onSubmit={handleSubmitUrl}>
            <div className="form-group">
              <label className="form-label">Public or Private Git URL *</label>
              <input
                type="url"
                required
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="form-input"
                placeholder="https://github.com/username/project.git"
              />
              <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem', display: 'block' }}>
                Full commit history will be cloned using Git CLI (avoiding GitHub API limits).
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">Personal Access Token (Optional)</label>
              <input
                type="password"
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
                className="form-input"
                placeholder="Single-use token for private repos (never stored in DB)"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Starter / Template Repo to Exclude (Optional)</label>
              <input
                type="url"
                value={starterRepoUrl}
                onChange={(e) => setStarterRepoUrl(e.target.value)}
                className="form-input"
                placeholder="https://github.com/course/hw1-starter.git"
              />
              <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem', display: 'block' }}>
                Any function matching this starter repo will be omitted from similarity flags.
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Start Date Filter (Optional)</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Deadline / End Date Filter (Optional)</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="form-input"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', marginTop: '1rem' }}
            >
              {loading ? 'Submitting & Queueing Clone...' : 'Analyze Git Repository'}
            </button>
          </form>
        )}

        {activeTab === 'zip' && (
          <form onSubmit={handleSubmitZip}>
            <div className="form-group">
              <label className="form-label">Select .zip Archive *</label>
              <input
                type="file"
                required
                accept=".zip"
                onChange={(e) => setZipFile(e.target.files[0] || null)}
                className="form-input"
                style={{ padding: '0.5rem' }}
              />
              <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.4rem', display: 'block' }}>
                <strong>Note:</strong> If the zip includes a <code>.git</code> folder, full commit history will be analyzed. 
                If no <code>.git</code> folder exists, it runs in similarity-only mode.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">Starter / Template Repo to Exclude (Optional)</label>
              <input
                type="url"
                value={zipStarterUrl}
                onChange={(e) => setZipStarterUrl(e.target.value)}
                className="form-input"
                placeholder="https://github.com/course/hw1-starter.git"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', marginTop: '1rem' }}
            >
              {loading ? 'Uploading & Extracting...' : 'Upload & Analyze Archive'}
            </button>
          </form>
        )}

        {activeTab === 'batch' && (
          <form onSubmit={handleSubmitBatch}>
            <div className="form-group">
              <label className="form-label">Repository URLs (One per line) *</label>
              <textarea
                required
                rows={5}
                value={batchUrls}
                onChange={(e) => setBatchUrls(e.target.value)}
                className="form-input font-mono"
                placeholder={"https://github.com/student1/project.git\nhttps://github.com/student2/project.git\nhttps://github.com/student3/project.git"}
                style={{ resize: 'vertical' }}
              />
              <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem', display: 'block' }}>
                Batch mode analyzes each repository and generates an all-pairs pairwise similarity matrix.
              </span>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', marginTop: '1rem' }}
            >
              {loading ? 'Queueing Batch Analyses...' : 'Start Batch Analysis'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
