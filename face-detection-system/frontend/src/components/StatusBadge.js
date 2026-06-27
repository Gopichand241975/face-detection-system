import React from 'react';

export default function StatusBadge({ connected, faceDetected }) {
  return (
    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '6px',
        padding: '4px 12px', borderRadius: '2px', fontSize: '11px',
        fontFamily: 'var(--font-mono)',
        background: connected ? 'rgba(0,255,65,0.1)' : 'rgba(255,107,53,0.1)',
        color: connected ? 'var(--accent)' : 'var(--warn)',
        border: `1px solid ${connected ? 'var(--accent)' : 'var(--warn)'}`,
      }}>
        <span style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: connected ? 'var(--accent)' : 'var(--warn)',
          animation: connected ? 'pulse 1.5s infinite' : 'none',
        }} />
        {connected ? 'CONNECTED' : 'OFFLINE'}
      </span>
      {connected && (
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          padding: '4px 12px', borderRadius: '2px', fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          background: faceDetected ? 'rgba(0,184,255,0.1)' : 'rgba(85,85,112,0.15)',
          color: faceDetected ? 'var(--accent2)' : 'var(--muted)',
          border: `1px solid ${faceDetected ? 'var(--accent2)' : 'var(--border)'}`,
        }}>
          <span style={{
            width: '6px', height: '6px', borderRadius: '50%',
            background: faceDetected ? 'var(--accent2)' : 'var(--muted)',
          }} />
          {faceDetected ? 'FACE DETECTED' : 'NO FACE'}
        </span>
      )}
    </div>
  );
}
