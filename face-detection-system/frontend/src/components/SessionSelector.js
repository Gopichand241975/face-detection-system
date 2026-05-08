import React, { useState } from 'react';

export default function SessionSelector({ sessionId, onSessionChange, disabled }) {
  const [input, setInput] = useState('');

  const handleNew = () => {
    const id = `session-${Date.now()}`;
    onSessionChange(id);
    setInput('');
  };

  const handleCustom = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSessionChange(input.trim());
      setInput('');
    }
  };

  return (
    <div className="panel">
      <div className="panel__title">Session</div>

      <div className="field">
        <div className="field__label">Current ID</div>
        <div className="field__value" style={{ fontSize: 11, wordBreak: 'break-all' }}>
          {sessionId}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button
          className="btn btn--primary"
          style={{ flex: 1, fontSize: 10, padding: '6px 0', clipPath: 'none' }}
          onClick={handleNew}
          disabled={disabled}
        >
          NEW SESSION
        </button>
      </div>

      <form onSubmit={handleCustom} style={{ marginTop: 10, display: 'flex', gap: 6 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="custom-id"
          disabled={disabled}
          style={{
            flex: 1,
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
            fontFamily: 'var(--mono)',
            fontSize: 11,
            padding: '5px 8px',
            outline: 'none',
          }}
        />
        <button
          type="submit"
          className="btn btn--primary"
          style={{ fontSize: 10, padding: '5px 10px', clipPath: 'none' }}
          disabled={disabled || !input.trim()}
        >
          USE
        </button>
      </form>
    </div>
  );
}
