import React, { useEffect, useState } from 'react';

const API = process.env.REACT_APP_API_URL || `http://${window.location.hostname}:8000`;

export default function ROIPanel({ roi, frameCount }) {
  // Poll /roi/{sessionId}/latest is done from StatsPanel
  // This panel receives roi via prop from App (passed from WS handler in future)
  // For now it also displays frame count and static roi info

  const hasROI = roi && roi.face_detected;

  return (
    <div className="panel">
      <div className="panel__title">Region of Interest</div>

      <div className="field">
        <div className="field__label">Face Detected</div>
        <div className={`field__value ${hasROI ? 'field__value--green' : 'field__value--danger'}`}>
          {roi == null ? '—' : hasROI ? '✓ YES' : '✗ NO'}
        </div>
      </div>

      {hasROI && roi.bounding_box && (
        <>
          <div className="field">
            <div className="field__label">Position (x, y)</div>
            <div className="field__value field__value--accent">
              {roi.bounding_box.x}, {roi.bounding_box.y}
            </div>
          </div>
          <div className="field">
            <div className="field__label">Size (w × h)</div>
            <div className="field__value field__value--accent">
              {roi.bounding_box.width} × {roi.bounding_box.height} px
            </div>
          </div>
          <div className="field">
            <div className="field__label">Confidence</div>
            <div className="field__value field__value--green">
              {roi.confidence != null ? `${(roi.confidence * 100).toFixed(1)}%` : '—'}
            </div>
          </div>
        </>
      )}

      <div className="field">
        <div className="field__label">Frames Processed</div>
        <div className="field__value field__value--accent">{frameCount.toLocaleString()}</div>
      </div>

      <div className="field">
        <div className="field__label">Frame #</div>
        <div className="field__value">{roi?.frame_number ?? '—'}</div>
      </div>

      {roi?.timestamp && (
        <div className="field">
          <div className="field__label">Last Update</div>
          <div className="field__value" style={{ fontSize: 11 }}>
            {new Date(roi.timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}
    </div>
  );
}
