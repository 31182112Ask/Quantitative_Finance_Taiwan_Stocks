import { useEffect, useRef, useState } from 'react';
import type { MarketSnapshot } from '../types';

const DEFAULT_WS_URL = 'ws://127.0.0.1:8000/ws/market';

export function useMarketStream() {
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);
  const [status, setStatus] = useState<'CONNECTING' | 'OPEN' | 'CLOSED'>('CONNECTING');
  const retryRef = useRef(0);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      setStatus('CONNECTING');
      socket = new WebSocket(import.meta.env.VITE_MARKET_WS_URL ?? DEFAULT_WS_URL);

      socket.onopen = () => {
        retryRef.current = 0;
        setStatus('OPEN');
      };
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as MarketSnapshot;
        if (message.type === 'snapshot') setSnapshot(message);
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        setStatus('CLOSED');
        if (disposed) return;
        const delay = Math.min(500 * 2 ** retryRef.current, 8_000);
        retryRef.current += 1;
        reconnectTimer = window.setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return { snapshot, status };
}
