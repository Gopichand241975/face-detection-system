import { useRef, useState, useCallback } from "react";

const API_BASE = process.env.REACT_APP_API_URL || "";

export default function useWebSocket() {
  const ws = useRef(null);
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const onFrameRef = useRef(null);
  const onRoiRef = useRef(null);

  const connect = useCallback((onFrame, onRoi) => {
    onFrameRef.current = onFrame;
    onRoiRef.current = onRoi;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const host = API_BASE.replace(/^https?:\/\//, "") || window.location.host;
    const sid = crypto.randomUUID();
    setSessionId(sid);
    const socket = new WebSocket(protocol + "://" + host + "/api/v1/ws/stream?session_id=" + sid);
    socket.binaryType = "arraybuffer";
    ws.current = socket;
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        const blob = new Blob([event.data], { type: "image/jpeg" });
        const url = URL.createObjectURL(blob);
        onFrameRef.current?.(url);
      } else {
        try { onRoiRef.current?.(JSON.parse(event.data)); } catch (_) {}
      }
    };
  }, []);

  const sendFrame = useCallback((blob) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(blob);
  }, []);

  const disconnect = useCallback(() => {
    ws.current?.close();
    ws.current = null;
  }, []);

  return { connect, disconnect, sendFrame, connected, sessionId };
}
