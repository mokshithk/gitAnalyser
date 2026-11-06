import React, { useState, useEffect } from 'react';
import { api, getToken } from './api';
import Navbar from './components/Navbar';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import NewAnalysisPage from './pages/NewAnalysisPage';
import AnalysisDetailPage from './pages/AnalysisDetailPage';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [currentPage, setCurrentPage] = useState('dashboard'); // 'dashboard', 'new', 'detail'
  const [selectedAnalysisId, setSelectedAnalysisId] = useState(null);

  useEffect(() => {
    const token = getToken();
    if (token) {
      api.getMe()
        .then((user) => {
          setCurrentUser(user);
        })
        .catch(() => {
          api.logout();
          setCurrentUser(null);
        })
        .finally(() => {
          setCheckingAuth(false);
        });
    } else {
      setCheckingAuth(false);
    }
  }, []);

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    setCurrentPage('dashboard');
  };

  const handleSelectAnalysis = (id) => {
    setSelectedAnalysisId(id);
    setCurrentPage('detail');
  };

  const handleAnalysisCreated = (id) => {
    setSelectedAnalysisId(id);
    setCurrentPage('detail');
  };

  if (checkingAuth) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f172a', color: '#94a3b8' }}>
        Initialising CodeProvenance...
      </div>
    );
  }

  if (!currentUser) {
    return <AuthPage onAuthSuccess={(user) => setCurrentUser(user)} />;
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        user={currentUser}
        currentPage={currentPage}
        onNavigate={(page) => {
          setCurrentPage(page);
          if (page !== 'detail') setSelectedAnalysisId(null);
        }}
        onLogout={handleLogout}
      />

      <main style={{ flex: 1 }}>
        {currentPage === 'dashboard' && (
          <DashboardPage
            onSelectAnalysis={handleSelectAnalysis}
            onNewAnalysis={() => setCurrentPage('new')}
          />
        )}

        {currentPage === 'new' && (
          <NewAnalysisPage
            onAnalysisCreated={handleAnalysisCreated}
            onCancel={() => setCurrentPage('dashboard')}
          />
        )}

        {currentPage === 'detail' && selectedAnalysisId && (
          <AnalysisDetailPage
            analysisId={selectedAnalysisId}
            onBack={() => {
              setCurrentPage('dashboard');
              setSelectedAnalysisId(null);
            }}
          />
        )}
      </main>
    </div>
  );
}
