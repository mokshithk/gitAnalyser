import React from 'react';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function ActivityHeatmap({ matrix }) {
  if (!matrix || matrix.length !== 7) {
    return <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No activity telemetry available.</div>;
  }

  // Find max value in matrix for intensity scale
  let maxVal = 1;
  for (let r = 0; r < 7; r++) {
    for (let c = 0; c < 24; c++) {
      if (matrix[r][c] > maxVal) maxVal = matrix[r][c];
    }
  }

  function getCellColor(val) {
    if (val === 0) return '#1e293b';
    const ratio = val / maxVal;
    if (ratio < 0.25) return '#14532d'; // low green
    if (ratio < 0.5) return '#15803d'; // mid green
    if (ratio < 0.75) return '#16a34a'; // high green
    return '#22c55e'; // max green
  }

  return (
    <div style={{ overflowX: 'auto', paddingBottom: '0.5rem' }}>
      <div style={{ minWidth: '600px' }}>
        {/* Hours Header */}
        <div style={{ display: 'grid', gridTemplateColumns: '40px repeat(24, 1fr)', gap: '3px', marginBottom: '4px' }}>
          <div></div>
          {HOURS.map(h => (
            <div key={h} style={{ fontSize: '0.65rem', color: '#64748b', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
              {h % 3 === 0 ? `${h}h` : ''}
            </div>
          ))}
        </div>

        {/* Days & Grid Cells */}
        {DAYS.map((day, dIdx) => (
          <div key={day} style={{ display: 'grid', gridTemplateColumns: '40px repeat(24, 1fr)', gap: '3px', marginBottom: '3px' }}>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'flex', alignItems: 'center' }}>
              {day}
            </div>
            {HOURS.map(h => {
              const count = matrix[dIdx][h] || 0;
              return (
                <div
                  key={h}
                  style={{
                    height: '18px',
                    borderRadius: '2px',
                    background: getCellColor(count),
                    border: '1px solid #0f172a',
                    cursor: 'pointer'
                  }}
                  title={`${day} at ${h}:00 &mdash; ${count} commit(s)`}
                />
              );
            })}
          </div>
        ))}

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.75rem', fontSize: '0.7rem', color: '#94a3b8' }}>
          <span>Less</span>
          <span style={{ width: '12px', height: '12px', background: '#1e293b', borderRadius: '2px' }}></span>
          <span style={{ width: '12px', height: '12px', background: '#14532d', borderRadius: '2px' }}></span>
          <span style={{ width: '12px', height: '12px', background: '#15803d', borderRadius: '2px' }}></span>
          <span style={{ width: '12px', height: '12px', background: '#22c55e', borderRadius: '2px' }}></span>
          <span>More</span>
        </div>
      </div>
    </div>
  );
}
