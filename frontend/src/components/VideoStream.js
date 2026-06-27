import React, { useRef, useEffect, useCallback, useState } from 'react';
import './VideoStream.css';

const WS_URL = process.env.REACT_APP_WS_URL || `ws://${window.location.hostname}:8000`;

export default function VideoStream({ sessionId, isStreaming, onStreamingChange, onROIUpdate }) {
  const videoRef  = useRef(null);   // <video> element (local camera preview)
  const canvasRef = useRef(null);   // canvas for capturing frames
  const outputRef = useRef(null);   // <img> to display annotated frames from server
  const wsRef     = useRef(null);
  const timerRef  = useRef(null);
  const [error, setError] = useState(null);
  const [fps, setFps] = useState(0);
  const fpsCounterRef = useRef({ count: 0, ts: Date.now() });

  // ── Start streaming ───────────────────────────────────────────────────────
  const startStream = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
    } catch (err) {
      setError('Camera access denied. Please allow camera permissions.');
      return;
    }

    // Open WebSocket
    const ws = new WebSocket(`${WS_URL}/video/ws/${sessionId}`);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      onStreamingChange(true);
      // Send frames at ~15 fps
      timerRef.current = setInterval(() => captureAndSend(ws), 66);
    };

    ws.onmessage = (ev) => {
      // Received annotated JPEG bytes from server
      const blob = new Blob([ev.data], { type: 'image/jpeg' });
      const url = URL.createObjectURL(blob);
      if (outputRef.current) {
        const old = outputRef.current.src;
        outputRef.current.src = url;
        if (old && old.startsWith('blob:')) URL.revokeObjectURL(old);
      }

      // FPS counter
      const now = Date.now();
      fpsCounterRef.current.count++;
      if (now - fpsCounterRef.current.ts >= 1000) {
        setFps(fpsCounterRef.current.count);
        fpsCounterRef.current = { count: 0, ts: now };
      }

      // Extract ROI from custom header — not available via WS, use a separate polling call
      // ROI data comes via /roi/{sessionId}/latest endpoint (polled by ROIPanel)
    };

    ws.onerror = () => setError('WebSocket error — is the backend running?');
    ws.onclose = () => { onStreamingChange(false); clearInterval(timerRef.current); };
  }, [sessionId, onStreamingChange]);

  // ── Capture & send ────────────────────────────────────────────────────────
  const captureAndSend = useCallback((ws) => {
    if (!videoRef.current || !canvasRef.current) return;
    if (ws.readyState !== WebSocket.OPEN) return;

    const ctx = canvasRef.current.getContext('2d');
    canvasRef.current.width  = videoRef.current.videoWidth  || 640;
    canvasRef.current.height = videoRef.current.videoHeight || 480;
    ctx.drawImage(videoRef.current, 0, 0);

    canvasRef.current.toBlob(
      (blob) => {
        if (blob && ws.readyState === WebSocket.OPEN) {
          blob.arrayBuffer().then(buf => ws.send(buf));
        }
      },
      'image/jpeg',
      0.8
    );
  }, []);

  // ── Stop streaming ────────────────────────────────────────────────────────
  const stopStream = useCallback(() => {
    clearInterval(timerRef.current);
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(t => t.stop());
      videoRef.current.srcObject = null;
    }
    onStreamingChange(false);
    setFps(0);
  }, [onStreamingChange]);

  // Cleanup on unmount
  useEffect(() => () => stopStream(), [stopStream]);

  return (
    <div className="video-container">
      {/* Hidden elements for capture */}
      <video ref={videoRef} className="video-hidden" playsInline muted />
      <canvas ref={canvasRef} className="video-hidden" />

      {/* Annotated output from server */}
      <div className="video-display">
        {isStreaming ? (
          <>
            <img ref={outputRef} className="video-output" alt="Annotated feed" />
            <div className="video-overlay-fps">
              <span className="fps-badge">{fps} FPS</span>
            </div>
          </>
        ) : (
          <div className="video-placeholder">
            <div className="video-placeholder__icon">◈</div>
            <div className="video-placeholder__text">
              {error || 'Press START to begin streaming'}
            </div>
            {error && (
              <div className="video-placeholder__hint">
                Make sure the backend is running and camera access is allowed.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="video-controls">
        {!isStreaming ? (
          <button className="btn btn--primary" onClick={startStream}>
            ▶ START STREAM
          </button>
        ) : (
          <button className="btn btn--danger" onClick={stopStream}>
            ■ STOP STREAM
          </button>
        )}
      </div>

      {error && !isStreaming && (
        <div className="video-error">{error}</div>
      )}
    </div>
  );
}
