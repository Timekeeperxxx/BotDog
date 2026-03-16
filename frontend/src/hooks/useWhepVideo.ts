import { useCallback, useEffect, useRef, useState } from 'react';

export type WhepStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WhepState {
  status: WhepStatus;
  error: string | null;
}

const DEFAULT_WHEP_URL = 'http://127.0.0.1:8889/cam/whep';

export function useWhepVideo() {
  const [state, setState] = useState<WhepState>({
    status: 'disconnected',
    error: null,
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const sessionUrlRef = useRef<string | null>(null);
  const connectingRef = useRef(false);
  const retryTimerRef = useRef<number | null>(null);

  const cleanup = useCallback(async () => {
    connectingRef.current = false;

    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }

    if (retryTimerRef.current) {
      window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }

    if (sessionUrlRef.current) {
      try {
        await fetch(sessionUrlRef.current, { method: 'DELETE' });
      } catch {
        // ignore cleanup errors
      }
      sessionUrlRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const connect = useCallback(async () => {
    if (state.status === 'connected' || connectingRef.current) {
      return;
    }

    const whepUrl = (import.meta.env.VITE_WHEP_URL as string | undefined) || DEFAULT_WHEP_URL;

    connectingRef.current = true;
    setState({ status: 'connecting', error: null });

    try {
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      });
      pcRef.current = pc;

      pc.addTransceiver('video', { direction: 'recvonly' });

      pc.ontrack = (event) => {
        if (videoRef.current) {
          videoRef.current.srcObject = event.streams[0];
        }
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'connected') {
          setState({ status: 'connected', error: null });
        } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
          setState({ status: 'error', error: 'WHEP 连接失败' });
          if (!retryTimerRef.current) {
            retryTimerRef.current = window.setTimeout(() => {
              retryTimerRef.current = null;
              void connect();
            }, 2000);
          }
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const response = await fetch(whepUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: offer.sdp,
      });

      if (!response.ok) {
        throw new Error(`WHEP 响应失败: ${response.status}`);
      }

      const sessionUrl = response.headers.get('Location');
      if (sessionUrl) {
        sessionUrlRef.current = sessionUrl;
      }

      const answerSdp = await response.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

      if (retryTimerRef.current) {
        window.clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }

      connectingRef.current = false;
    } catch (error) {
      await cleanup();
      connectingRef.current = false;
      setState({ status: 'error', error: String(error) });
      if (!retryTimerRef.current) {
        retryTimerRef.current = window.setTimeout(() => {
          retryTimerRef.current = null;
          void connect();
        }, 2000);
      }
    }
  }, [cleanup, state.status]);

  const disconnect = useCallback(async () => {
    await cleanup();
    setState({ status: 'disconnected', error: null });
  }, [cleanup]);

  useEffect(() => {
    return () => {
      void cleanup();
    };
  }, [cleanup]);

  return {
    status: state,
    videoRef,
    connect,
    disconnect,
  };
}
