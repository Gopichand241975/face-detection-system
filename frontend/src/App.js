import React, { useRef, useState, useEffect, useCallback } from 'react';
import useWebSocket from './hooks/useWebSocket';
import StatusBadge from './components/StatusBadge';
import ROITable from './components/ROITable';
import { fetchROI } from './utils/api';
import './App.css';

export default function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const prevUrlRef = useRef(null);

  const [streaming, setStreaming] = useState(false);
  const [faceDetected, setFaceDetected] = useState(false);
  const [latestROI, setLatestROI] = useState(null);
  const [roiHistory, setRoiHistory] = useState([]);
  const [annotatedSrc, setAnnotatedSrc] = useState(null);
  const [frameCount, setFrameCount] = useState(0);
  const [fps, setFps] = useState(0);
  const fpsRef = useRef({ count: 0, last: Date.now() });

  const { connect, disconnect, sendFrame, connected, sessionId } = useWebSocket();

  // ROI polling
  useEffect(() => {
    if (!sessionId || !connected) return;
    const poll = setInterval(async () => {
      try {
        const data = await fetchROI(sessionId, 50);
        setRoiHistory(data.records || []);
      } catch (_) {}
    }, 2000);
    return () => clearInterval(poll);
  }, [sessionId, connected]);

  const handleAnnotatedFrame = useCallback((url) => {
    if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current);
    prevUrlRef.current = url;
    setAnnotatedSrc(url);
    setFrameCount(c => c + 1);
    const now = Date.now();
    fpsRef.current.count++;
    if (now - fpsRef.current.last >= 1000) {
      setFps(fpsRef.current.count);
      fpsRef.current = { count: 0, last: now };
    }
  }, []);

  const handleROIMeta = useCallback((data) => {
    setFaceDetected(data.face_detected);
    if (data.roi) setLatestROI(data.roi);
  }, []);

  const startStreaming = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      connect(handleAnnotatedFrame, handleROIMeta);
      setStreaming(true);

      intervalRef.current = setInterval(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas || video.readyState < 2) return;
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(blob => { if (blob) sendFrame(blob); }, 'image/jpeg', 0.7);
      }, 100); // 10 fps capture
    } catch (err) {
      alert('Camera access denied: ' + err.message);
    }
  };

  const stopStreaming = () => {
    clearInterval(intervalRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    disconnect();
    setStreaming(false);
    setFaceDetected(false);
    setAnnotatedSrc(null);
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-icon">◈</span>
            <span className="logo-text">FACE<span className="accent">DETECT</span></span>
          </div>
          <div className="subtitle">Real-Time Detection System v1.0</div>
        </div>
        <div className="header-right">
          <StatusBadge connected={connected} faceDetected={faceDetected} />
          <div className="stats">
            <span className="stat"><span className="stat-label">FPS</span><span className="stat-val accent">{fps}</span></span>
            <span className="stat"><span className="stat-label">FRAMES</span><span className="stat-val">{frameCount}</span></span>
          </div>
        </div>
      </header>

      <main className="main">
        {/* Video Panel */}
        <section className="video-panel">
          <div className="panel-header">
            <span className="panel-title">VIDEO FEED</span>
            <div className="scan-line" />
          </div>

          <div className="video-container">
            {/* Hidden raw video + canvas for capture */}
            <video ref={videoRef} style={{ display: 'none' }} muted playsInline />
            <canvas ref={canvasRef} style={{ display: 'none' }} />

            {annotatedSrc ? (
              <img src={annotatedSrc} alt="Annotated feed" className="annotated-feed" />
            ) : (
              <div className="no-feed">
                <div className="no-feed-icon">◉</div>
                <div className="no-feed-text">AWAITING SIGNAL</div>
                <div className="no-feed-sub">Start streaming to activate detection</div>
              </div>
            )}

            {faceDetected && (
              <div className="detection-overlay">
                <span className="detection-label">FACE LOCKED</span>
              </div>
            )}
          </div>

          <div className="controls">
            {!streaming ? (
              <button className="btn btn-primary" onClick={startStreaming}>
                <span>▶</span> START STREAM
              </button>
            ) : (
              <button className="btn btn-danger" onClick={stopStreaming}>
                <span>■</span> STOP STREAM
              </button>
            )}
            {sessionId && (
              <div className="session-id">
                SESSION: <span className="accent">{sessionId.slice(0, 8)}…</span>
              </div>
            )}
          </div>
        </section>

        {/* Data Panel */}
        <section className="data-panel">
          {/* Current ROI */}
          <div className="roi-card">
            <div className="panel-header">
              <span className="panel-title">CURRENT ROI</span>
            </div>
            {latestROI ? (
              <div className="roi-grid">
                {[
                  ['X', latestROI.x?.toFixed(1)],
                  ['Y', latestROI.y?.toFixed(1)],
                  ['WIDTH', latestROI.width?.toFixed(1)],
                  ['HEIGHT', latestROI.height?.toFixed(1)],
                  ['CONFIDENCE', (latestROI.confidence * 100).toFixed(1) + '%'],
                  ['FRAME', latestROI.frame_number],
                ].map(([label, val]) => (
                  <div key={label} className="roi-item">
                    <div className="roi-label">{label}</div>
                    <div className="roi-val">{val ?? '—'}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">No detection yet</div>
            )}
          </div>

          {/* History Table */}
          <div className="history-card">
            <div className="panel-header">
              <span className="panel-title">ROI HISTORY</span>
              <span className="badge">{roiHistory.length}</span>
            </div>
            <ROITable records={roiHistory} />
          </div>
        </section>
      </main>
    </div>
  );
}
