import React from 'react';

const cell = {
  padding: '8px 12px',
  borderBottom: '1px solid var(--border)',
  fontSize: '11px',
  fontFamily: 'var(--font-mono)',
  color: 'var(--text)',
};

const headCell = {
  ...cell,
  color: 'var(--accent)',
  borderBottom: '1px solid var(--accent)',
  fontWeight: '700',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
};

export default function ROITable({ records }) {
  if (!records || records.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)', fontSize: '12px' }}>
        NO ROI DATA YET
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto', overflowY: 'auto', maxHeight: '280px' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
        <thead>
          <tr>
            {['Frame', 'X', 'Y', 'W', 'H', 'Confidence', 'Timestamp'].map(h => (
              <th key={h} style={headCell}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.id} style={{ transition: 'background 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,255,65,0.04)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <td style={cell}>{r.frame_number}</td>
              <td style={cell}>{r.x.toFixed(1)}</td>
              <td style={cell}>{r.y.toFixed(1)}</td>
              <td style={cell}>{r.width.toFixed(1)}</td>
              <td style={cell}>{r.height.toFixed(1)}</td>
              <td style={{ ...cell, color: 'var(--accent)' }}>{(r.confidence * 100).toFixed(1)}%</td>
              <td style={{ ...cell, color: 'var(--muted)' }}>
                {new Date(r.timestamp).toLocaleTimeString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
