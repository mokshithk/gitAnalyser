import React from 'react';

export default function Navbar({ user, onNavigate, onLogout, currentPage }) {
  return (
    <nav style={{
      background: '#1e293b',
      borderBottom: '1px solid #334155',
      padding: '0.875rem 0',
      position: 'sticky',
      top: 0,
      zIndex: 40
    }}>
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Brand */}
        <div 
          onClick={() => onNavigate('dashboard')} 
          style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}
        >
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            background: 'linear-gradient(135deg, #22c55e 0%, #0284c7 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            color: '#0f172a',
            fontSize: '1rem'
          }}>
            CP
          </div>
          <div>
            <span style={{ fontWeight: 700, fontSize: '1.125rem', letterSpacing: '-0.02em', color: '#f8fafc' }}>
              CodeProvenance
            </span>
            <span style={{ fontSize: '0.7rem', color: '#94a3b8', marginLeft: '0.5rem', fontFamily: 'var(--font-mono)' }}>
              TRIAGE v1.0
            </span>
          </div>
        </div>

        {/* Links & User */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {user && (
            <>
              <button 
                onClick={() => onNavigate('dashboard')}
                className="btn btn-secondary"
                style={{
                  background: currentPage === 'dashboard' ? '#334155' : 'transparent',
                  borderColor: currentPage === 'dashboard' ? '#0284c7' : '#334155'
                }}
              >
                Dashboard
              </button>

              <button 
                onClick={() => onNavigate('new')}
                className="btn btn-primary"
              >
                + New Analysis
              </button>

              <div style={{
                background: '#0b1120',
                border: '1px solid #334155',
                padding: '0.35rem 0.75rem',
                borderRadius: '9999px',
                fontSize: '0.8rem',
                color: '#cbd5e1',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e' }}></span>
                <span>{user.email}</span>
                {user.role === 'admin' && (
                  <span style={{ background: '#3b82f6', color: '#fff', fontSize: '0.65rem', padding: '0.1rem 0.35rem', borderRadius: '4px' }}>
                    ADMIN
                  </span>
                )}
              </div>

              <button 
                onClick={onLogout}
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                title="Log out of account"
              >
                Sign out
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
