import { useRef, useState, useCallback, useEffect } from 'react';

export interface WSEvent {
  type: string;
  data: Record<string, any>;
  timestamp?: number;
}

interface UseWebSocketReturn {
  connected: boolean;
  events: WSEvent[];
  sendMessage: (payload: Record<string, any>) => void;
  clearEvents: () => void;
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<WSEvent[]>([]);
  const reconnectTimer = useRef<number>();

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('WebSocket connected');
      };

      ws.onmessage = (e) => {
        try {
          const event: WSEvent = JSON.parse(e.data);
          event.timestamp = Date.now();
          setEvents((prev) => [...prev, event]);
        } catch (err) {
          console.error('Failed to parse WS message:', err);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        console.log('WebSocket disconnected, reconnecting in 3s...');
        reconnectTimer.current = window.setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        ws.close();
      };
    } catch (err) {
      console.error('WebSocket connection failed:', err);
      reconnectTimer.current = window.setTimeout(connect, 3000);
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((payload: Record<string, any>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { connected, events, sendMessage, clearEvents };
}
