import React from 'react';
import './Header.css';

export default function Header({ isStreaming, sessionId }) {
  return (
    <header className="header">
      <div className="header__logo">
        <span className="header__logo-icon">◈</span>
        <span className="header__title">FACE<span className="header__title-accent">DETECT</span></span>
        <span className="header__subtitle">Real-Time Vision System</span>
      </div>

      <div className="header__status">
        <div className={`status-pill ${isStreaming ? 'status-pill--live' : 'status-pill--idle'}`}>
          <span className="status-pill__dot" />
          {isStreaming ? 'LIVE' : 'IDLE'}
        </div>
      </div>

      <div className="header__meta">
        <span className="header__meta-label">SESSION</span>
        <span className="header__meta-value">{sessionId}</span>
      </div>
    </header>
  );
}
