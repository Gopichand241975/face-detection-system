const BASE = process.env.REACT_APP_API_URL || '';

export async function fetchROI(sessionId, limit = 20) {
  const url = sessionId
    ? `${BASE}/api/v1/roi?session_id=${sessionId}&limit=${limit}`
    : `${BASE}/api/v1/roi`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`ROI fetch failed: ${res.status}`);
  return res.json();
}

export function getMJPEGUrl(sessionId) {
  return `${BASE}/api/v1/stream/feed?session_id=${sessionId}`;
}
