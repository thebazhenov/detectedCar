import React, { useEffect, useRef, useState } from "react";

interface Props {
  token: string;
  mjpegUrl?: string; // optional override; defaults to /video/stream
  wsUrl?: string; // optional override; defaults to /ws/video
}

export const VideoStream: React.FC<Props> = ({ token, mjpegUrl, wsUrl }) => {
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [useMjpeg, setUseMjpeg] = useState(true);

  const mjpeg = mjpegUrl || `/video/stream?token=${token}`;
  const wsEndpoint = wsUrl || `${(window.location.protocol === "https:" ? "wss:" : "ws:")}//${window.location.host}/ws/video?token=${token}`;

  useEffect(() => {
    // Try to load MJPEG first by setting <img src=>; if it fails repeatedly, fallback to WebSocket
    let failedCount = 0;
    const img = imgRef.current;
    const onError = () => {
      failedCount += 1;
      if (failedCount >= 3) {
        setUseMjpeg(false);
      }
    };
    if (img) {
      img.addEventListener("error", onError);
      img.src = mjpeg;
    }
    return () => {
      if (img) {
        img.removeEventListener("error", onError);
      }
    };
  }, [mjpeg, token]);

  useEffect(() => {
    if (useMjpeg) return;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsEndpoint);
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
      ws.onerror = () => setWsConnected(false);
      ws.onmessage = (ev) => {
        // server sends base64-encoded JPEG
        try {
          const b64 = ev.data as string;
          const img = imgRef.current;
          if (img) {
            img.src = `data:image/jpeg;base64,${b64}`;
          }
        } catch (e) {
          // ignore
        }
      };
    } catch (e) {
      console.error("WS connect error", e);
    }
    return () => {
      if (ws) ws.close();
    };
  }, [useMjpeg, wsEndpoint]);

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <strong>Stream</strong> — {useMjpeg ? "MJPEG" : "WebSocket"} {wsConnected ? "(WS connected)" : ""}
      </div>
      <img
        ref={imgRef}
        alt="video-stream"
        style={{ width: "100%", maxHeight: 720, objectFit: "contain", background: "black" }}
      />
    </div>
  );
};

export default VideoStream;
