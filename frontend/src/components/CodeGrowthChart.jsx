import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function CodeGrowthChart({ timeline }) {
  if (!timeline || timeline.length === 0) {
    return <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No growth history data available.</div>;
  }

  const labels = timeline.map(item => item.sha);
  const totalLinesData = timeline.map(item => item.total_lines);
  const additionsData = timeline.map(item => item.lines_added);

  const data = {
    labels,
    datasets: [
      {
        label: 'Net Codebase Lines',
        data: totalLinesData,
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 6,
      },
      {
        label: 'Lines Added (Per Commit)',
        data: additionsData,
        borderColor: '#38bdf8',
        backgroundColor: 'rgba(56, 189, 248, 0.2)',
        borderDash: [4, 4],
        fill: false,
        tension: 0.2,
        pointRadius: 2,
      }
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#cbd5e1',
          font: { family: "'IBM Plex Sans', sans-serif", size: 12 },
        },
      },
      tooltip: {
        backgroundColor: '#0f172a',
        borderColor: '#334155',
        borderWidth: 1,
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        titleFont: { family: "'JetBrains Mono', monospace" },
      },
    },
    scales: {
      x: {
        grid: { color: '#1e293b' },
        ticks: { color: '#64748b', font: { family: "'JetBrains Mono', monospace", size: 10 } },
      },
      y: {
        grid: { color: '#1e293b' },
        ticks: { color: '#64748b', font: { family: "'JetBrains Mono', monospace", size: 10 } },
      },
    },
  };

  return (
    <div style={{ height: '280px', width: '100%' }}>
      <Line data={data} options={options} />
    </div>
  );
}
