import React, { useEffect, useState, useRef, useCallback } from 'react';

const API = process.env.REACT_APP_API_URL || `http://${window.location.hostname}:8000`;

export default function StatsPanel({ sessionId, isStreaming }) {
  const [stats, setStats]         = useState(null);
  const [latestROI, setLatestROI] = useState(null);
  const [sessions, setSessions]   = useState([]);
  const [error, setError]         = useState(null);
  const intervalRef = useRef(null);

  const fetchData = useCallback(async () => {
    if (!sessionId) return;
    try {
      // Stats
      const sRes = await fetch(`${API}/roi/${sessionId}/stats`);
      if (sRes.ok) setStats(await sRes.json());

      // Latest ROI
      const rRes = await fetch(`${API}/roi/${sessionId}/latest`);
      if (rRes.ok) setLatestROI(await rRes.json());

      // Sessions list
      const lRes = await fetch(`${API}/roi/sessions?limit=5`);
      if (lRes.ok) {
        const data = await lRes.json();
        setSessions(data.sessions || []);
      }

      setError(null);
    } catch (e) {
      setError('Cannot reach backend');
    }
  }, [sessionId]);

  useEffect(() => {
    fetchData();
    if (isStreaming) {
      intervalRef.current = setInterval(fetchData, 2000);
    }
    return () => clearInterval(intervalRef.current);
  }, [fetchData, isStreaming]);

  return (
    <>
      {/* Live stats */}
      <div className="panel">
        <div className="panel__title">Session Stats</div>
        {error && (
          <div style={{ color: 'var(--danger)', fontFamily: 'var(--mono)', fontSize: 11 }}>
            {error}
          </div>
        )}
        {stats ? (
          <>
            <div className="field">
              <div className="field__label">Total Frames</div>
              <div className="field__value field__value--accent">
                {stats.total_frames?.toLocaleString()}
              </div>
            </div>
            <div className="field">
              <div className="field__label">Face Frames</div>
              <div className="field__value field__value--green">
                {stats.frames_with_face?.toLocaleString()}
              </div>
            </div>
            <div className="field">
              <div className="field__label">Detection Rate</div>
              <div className="field__value">
                {stats.detection_rate != null
                  ? `${(stats.detection_rate * 100).toFixed(1)}%`
                  : '—'}
              </div>
            </div>
            <div className="field">
              <div className="field__label">Avg Confidence</div>
              <div className="field__value">
                {stats.avg_confidence != null
                  ? `${(stats.avg_confidence * 100).toFixed(1)}%`
                  : '—'}
              </div>
            </div>
            {stats.started_at && (
              <div className="field">
                <div className="field__label">Started</div>
                <div className="field__value" style={{ fontSize: 11 }}>
                  {new Date(stats.started_at).toLocaleTimeString()}
                </div>
              </div>
            )}
          </>
        ) : (
          <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--mono)', fontSize: 11 }}>
            No data yet — start streaming.
          </div>
        )}
      </div>

      {/* Latest ROI raw data */}
      {latestROI && (
        <div className="panel">
          <div className="panel__title">Latest ROI Record</div>
          <pre style={{
            fontFamily: 'var(--mono)',
            fontSize: 10,
            color: 'var(--text-dim)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            lineHeight: 1.6,
          }}>
            {JSON.stringify(latestROI, null, 2)}
          </pre>
        </div>
      )}

      {/* Recent sessions */}
      <div className="panel">
        <div className="panel__title">Recent Sessions</div>
        {sessions.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--mono)', fontSize: 11 }}>
            None yet
          </div>
        ) : (
          sessions.map(s => (
            <div key={s.session_id} className="field" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 8, marginBottom: 8 }}>
              <div className="field__label">{s.session_id.slice(0, 24)}…</div>
              <div className="field__value" style={{ fontSize: 11 }}>
                {s.frame_count} frames · {new Date(s.last_active).toLocaleTimeString()}
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );
}
