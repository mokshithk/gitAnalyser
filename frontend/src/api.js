const API_BASE = '/api';

export function getToken() {
  return localStorage.getItem('cp_token');
}

export function setToken(token) {
  if (token) {
    localStorage.setItem('cp_token', token);
  } else {
    localStorage.removeItem('cp_token');
  }
}

async function request(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // If not FormData, default to application/json
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    setToken(null);
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/';
    }
  }

  if (!res.ok) {
    let errorDetail = 'Request failed';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = await res.text();
    }
    throw new Error(errorDetail || `HTTP ${res.status}`);
  }

  if (res.status === 204) {
    return null;
  }

  return res.json();
}

export const api = {
  // Auth
  async login(email, password) {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return data;
  },

  async register(email, password, role = 'user') {
    const data = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, role }),
    });
    setToken(data.access_token);
    return data;
  },

  async getMe() {
    return request('/auth/me');
  },

  logout() {
    setToken(null);
  },

  // Analyses
  async submitGitUrl(payload) {
    return request('/analyses/git-url', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async submitZip(file, starterRepoUrl) {
    const formData = new FormData();
    formData.append('file', file);
    if (starterRepoUrl) {
      formData.append('starter_repo_url', starterRepoUrl);
    }
    return request('/analyses/zip', {
      method: 'POST',
      body: formData,
    });
  },

  async listAnalyses(params = {}) {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.mode) query.append('mode', params.mode);
    if (params.search) query.append('search', params.search);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/analyses${qs}`);
  },

  async getAnalysis(id) {
    return request(`/analyses/${id}`);
  },

  async deleteAnalysis(id) {
    return request(`/analyses/${id}`, { method: 'DELETE' });
  },

  async getCommits(analysisId, limit = 100, offset = 0) {
    return request(`/analyses/${analysisId}/commits?limit=${limit}&offset=${offset}`);
  },

  async getCommitMetrics(analysisId) {
    return request(`/analyses/${analysisId}/commit-metrics`);
  },

  async getFlags(analysisId) {
    return request(`/analyses/${analysisId}/flags`);
  },

  async updateFlag(analysisId, flagId, payload) {
    return request(`/analyses/${analysisId}/flags/${flagId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async getMatches(analysisId) {
    return request(`/analyses/${analysisId}/matches`);
  },

  async getReport(analysisId) {
    return request(`/analyses/${analysisId}/report`);
  },

  getPdfUrl(analysisId) {
    const token = getToken();
    return `${API_BASE}/analyses/${analysisId}/report/pdf`;
  },

  async downloadPdf(analysisId) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/report/pdf`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) throw new Error('Failed to generate PDF');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CodeProvenance_Report_${analysisId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  },
};
