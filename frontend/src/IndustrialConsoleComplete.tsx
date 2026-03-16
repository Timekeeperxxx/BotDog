/**
 * BotDog 机器狗控制终端 - 完整集成版本
 * 包含完整的前后端交互、WebSocket连接和WHEP视频流
 */

import { useState, useEffect, useRef } from 'react';
import { useBotDogWebSocket } from './hooks/useBotDogWebSocket';
import { useWhepVideo } from './hooks/useWhepVideo';
import { ConfigPanel } from './components/ConfigPanel';

// ==================== 顶部状态栏 ====================
function HeaderBar({
  latency,
  temperature,
  battery,
  onEmergencyStop,
  onToggleFullscreen,
  onOpenConfig
}: {
  latency: string;
  temperature: string;
  battery: string;
  onEmergencyStop: () => void;
  onToggleFullscreen: () => void;
  onOpenConfig: () => void;
}) {

  return (
    <header style={{
      height: '48px',
      borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      background: '#0f1115',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ color: '#ffffff', fontWeight: 900, letterSpacing: '-0.04em' }}>BOTDOG</span>
          <span style={{ fontSize: '10px', color: '#3b82f6', fontWeight: 700, letterSpacing: '-0.02em' }}>V5.0 核心数据终端</span>
        </div>
        <div style={{
          display: 'flex',
          gap: '16px',
          fontSize: '11px',
          fontFamily: '"JetBrains Mono", monospace',
          borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
          paddingLeft: '20px',
        }}>
          <span style={{ color: parseFloat(battery) < 20 ? '#ef4444' : '#10b981' }}>电池: {battery}</span>
          <span style={{ color: '#94a3b8' }}>延迟: {latency}</span>
          <span style={{ color: '#94a3b8' }}>温度: {temperature}</span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={onOpenConfig}
          style={{
            height: '32px',
            padding: '0 14px',
            fontSize: '11px',
            background: '#1f2937',
            color: '#e2e8f0',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          设置
        </button>
        <button
          onClick={onToggleFullscreen}
          style={{
            height: '32px',
            padding: '0 14px',
            fontSize: '11px',
            background: '#1e293b',
            color: '#93c5fd',
            border: '1px solid rgba(59, 130, 246, 0.35)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          全屏
        </button>
        <button
          onClick={onEmergencyStop}
          style={{
            height: '32px',
            padding: '0 14px',
            fontSize: '11px',
            background: '#2b0b0b',
            color: '#f87171',
            border: '1px solid rgba(248, 113, 113, 0.35)',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          紧急停机
        </button>
      </div>
    </header>
  );
}

// ==================== 左侧栏 ====================
function LeftPanel({
  latency,
  battery,
  temperature,
  groundspeed,
  angularVel,
  resolution,
  rssi,
  logs
}: {
  latency: string;
  battery: string;
  temperature: string;
  groundspeed: string;
  angularVel: string;
  resolution: string;
  rssi: string;
  logs: Array<{ timestamp: number; module: string; message: string; level: string }>;
}) {
  const rows = [
    { label: '延迟', value: latency, unit: 'ms' },
    { label: '信号', value: rssi, unit: 'dBm' },
    { label: '温度', value: temperature, unit: '°C' },
    { label: '电池', value: battery, unit: '%' },
    { label: '线速度', value: groundspeed, unit: 'm/s' },
    { label: '角速度', value: angularVel, unit: '°/s' },
  ];

  return (
    <aside style={{
      width: '260px',
      borderRight: '1px solid rgba(255, 255, 255, 0.1)',
      background: '#0f1115',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        padding: '16px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        background: '#0f1115',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#60a5fa',
          fontSize: '11px',
          fontWeight: 700,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          marginBottom: '16px',
        }}>
          行走数据监控
        </div>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: '11px',
        }}>
          {rows.map((row) => (
            <div
              key={row.label}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                paddingBottom: '8px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
              }}
            >
              <span style={{ color: '#64748b' }}>{row.label}</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                <span style={{ color: '#f1f5f9', fontWeight: 700 }}>{row.value}</span>
                {row.unit && (
                  <span style={{ fontSize: '10px', color: '#475569', fontWeight: 500 }}>{row.unit}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{
        padding: '12px 16px',
        fontSize: '10px',
        color: '#94a3b8',
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        fontFamily: '"JetBrains Mono", monospace',
      }}>
        分辨率: {resolution}
      </div>

      <div style={{
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(255, 255, 255, 0.02)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}>
        <div style={{
          padding: '10px 16px',
          fontSize: '10px',
          color: '#94a3b8',
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          fontWeight: 700,
        }}>
          运行日志
        </div>
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '0 16px 12px',
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: '11px',
          color: '#94a3b8',
        }}>
          {logs.length === 0 ? (
            <div style={{ color: '#64748b' }}>等待日志数据...</div>
          ) : (
            logs.map((log, index) => (
              <div key={`${log.timestamp}-${index}`} style={{ display: 'flex', gap: '6px', lineHeight: 1.6 }}>
                <span style={{ color: '#475569', whiteSpace: 'nowrap' }}>
                  {new Date(log.timestamp * 1000).toLocaleTimeString([], { hour12: false, minute: '2-digit', second: '2-digit' })}
                </span>
                <span style={{ color: '#64748b' }}>[{log.module}]</span>
                <span style={{ color: log.level === 'error' ? '#f87171' : log.level === 'warning' ? '#f59e0b' : '#34d399' }}>
                  {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
// ==================== 中央视频区域 ====================
function VideoSection({
  isFullscreen,
  videoRef,
  whepStatus,
  isConnected,
  resolutionLabel,
  rssi
}: {
  isFullscreen: boolean;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  whepStatus: { status: string; error: string | null };
  isConnected: boolean;
  resolutionLabel: string;
  rssi: string;
}) {

  const whepConfig: any = {
    'disconnected': { color: '#ef4444', text: '未连接' },
    'connecting': { color: '#f59e0b', text: '连接中...' },
    'connected': { color: '#10b981', text: '已连接' },
    'error': { color: '#ef4444', text: whepStatus.error || '错误' },
  };

  const currentWhepStatus = whepConfig[whepStatus.status as keyof typeof whepConfig] || whepConfig.disconnected;

  return (
    <section style={isFullscreen ? {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      width: '100vw',
      height: '100vh',
      zIndex: 9999,
      borderRadius: 0,
      border: 'none',
      margin: 0,
      padding: 0,
      background: 'black',
    } : {
      flex: 1,
      background: 'black',
      borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
      borderRight: '1px solid rgba(255, 255, 255, 0.1)',
      position: 'relative',
    }}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          background: 'black',
        }}
      />

      {whepStatus.status !== 'connected' && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(15, 23, 42, 0.88)',
          zIndex: 5,
        }}>
          <div style={{ fontSize: '48px', marginBottom: '1rem', opacity: 0.5 }}>📹</div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#e2e8f0', marginBottom: '0.5rem' }}>
            视频流 {currentWhepStatus.text}
          </div>
          {whepStatus.error && (
            <div style={{
              fontSize: '14px',
              color: '#ef4444',
              marginBottom: '1rem',
              padding: '0.5rem 1rem',
              background: 'rgba(239, 68, 68, 0.1)',
              borderRadius: '4px',
            }}>
              {whepStatus.error}
            </div>
          )}
          <div style={{ fontSize: '12px', color: '#64748b' }}>
            {isConnected ? '等待WHEP连接...' : '等待后端连接...'}
          </div>
        </div>
      )}

      <div style={{
        position: 'absolute',
        top: '16px',
        left: '16px',
        zIndex: 10,
      }}>
        <div style={{
          background: 'rgba(0, 0, 0, 0.6)',
          borderLeft: '2px solid #3b82f6',
          padding: '10px 12px',
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: '10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase' }}>当前清晰度:</span>
            <span style={{ color: '#e2e8f0', fontWeight: 700 }}>{resolutionLabel}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase' }}>连接状态:</span>
            <span style={{ color: currentWhepStatus.color, fontWeight: 700 }}>
              {currentWhepStatus.text}
            </span>
          </div>
          <div style={{
            paddingTop: '6px',
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            color: 'rgba(255, 255, 255, 0.35)',
            textTransform: 'uppercase',
          }}>
            信号强度: {rssi} dBm
          </div>
        </div>
        {isFullscreen && (
          <div style={{
            marginTop: '8px',
            background: 'rgba(255, 255, 255, 0.05)',
            color: '#94a3b8',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '9px',
            fontWeight: 'bold',
          }}>
            按 ESC 或 F11 退出全屏
          </div>
        )}
      </div>

    </section>
  );
}

// ==================== 底部状态条 ====================
function FooterBar({ systemStatus, isConnected }: { systemStatus: { status: string; uptime: string }; isConnected: boolean }) {
  const statusConfig: any = {
    'DISCONNECTED': { icon: '🔴', text: '未连接', color: '#ef4444' },
    'STANDBY': { icon: '🟡', text: '待机中', color: '#f59e0b' },
    'IN_MISSION': { icon: '🟢', text: '任务中', color: '#10b981' },
    'E_STOP_TRIGGERED': { icon: '🚨', text: '紧急停止', color: '#ef4444' },
  };

  const config = statusConfig[systemStatus.status] || statusConfig.DISCONNECTED;

  return (
    <footer style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '6px 24px',
      fontSize: '9px',
      color: '#475569',
      textTransform: 'uppercase',
      letterSpacing: '2px',
      borderTop: '1px solid rgba(255, 255, 255, 0.08)',
      background: '#0a0c10',
    }}>
      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: config.color }}>
          {config.icon} {config.text}
        </span>
        <span>运行时间: {systemStatus.uptime}</span>
      </div>
      <span>安全加密层: AES-XTS-256 {isConnected && '| 实时连接中'}</span>
    </footer>
  );
}

// ==================== 主应用 ====================
export default function IndustrialConsoleComplete() {
  const {
    telemetry,
    isConnected,
    systemStatus,
    logs,
    addLog,
    triggerEmergencyStop,
    connect: connectWs,
    disconnect: disconnectWs,
  } = useBotDogWebSocket();

  const startupLoggedRef = useRef(false);
  const lastWsStatusRef = useRef<boolean | null>(null);
  const lastWhepStatusRef = useRef<string | null>(null);
  const wsDelayTimerRef = useRef<number | null>(null);
  const whepDelayTimerRef = useRef<number | null>(null);

  const { status: whepStatus, videoRef, connect: connectWhep, disconnect: disconnectWhep } = useWhepVideo();

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showConfigPanel, setShowConfigPanel] = useState(false);

  useEffect(() => {
    connectWs();
    return () => {
      disconnectWs();
    };
  }, []);

  // WHEP 连接与遥测连接解耦，独立尝试连接
  useEffect(() => {
    connectWhep();
    return () => {
      disconnectWhep();
    };
  }, []);

  useEffect(() => {
    if (startupLoggedRef.current) return;
    startupLoggedRef.current = true;
    addLog('系统启动检查开始', 'info', 'STARTUP');
  }, [addLog]);

  useEffect(() => {
    if (lastWsStatusRef.current === isConnected) {
      return;
    }
    lastWsStatusRef.current = isConnected;

    if (isConnected) {
      if (wsDelayTimerRef.current) {
        window.clearTimeout(wsDelayTimerRef.current);
        wsDelayTimerRef.current = null;
      }
      addLog('遥测链路已连接', 'info', 'WS');
      return;
    }

    if (wsDelayTimerRef.current) {
      window.clearTimeout(wsDelayTimerRef.current);
    }
    wsDelayTimerRef.current = window.setTimeout(() => {
      if (!isConnected) {
        addLog('遥测链路未连接', 'error', 'WS');
      }
      wsDelayTimerRef.current = null;
    }, 3000);
  }, [isConnected, addLog]);

  useEffect(() => {
    if (lastWhepStatusRef.current === whepStatus.status) {
      return;
    }
    lastWhepStatusRef.current = whepStatus.status;

    if (whepStatus.status === 'connected') {
      if (whepDelayTimerRef.current) {
        window.clearTimeout(whepDelayTimerRef.current);
        whepDelayTimerRef.current = null;
      }
      addLog('视频流连接成功', 'info', 'WHEP');
      return;
    }

    if (whepStatus.status === 'connecting') {
      addLog('视频流连接中', 'info', 'WHEP');
      return;
    }

    if (whepDelayTimerRef.current) {
      window.clearTimeout(whepDelayTimerRef.current);
    }

    if (whepStatus.status === 'error') {
      addLog(`视频流连接失败: ${whepStatus.error || '未知错误'}`, 'error', 'WHEP');
      return;
    }

    if (whepStatus.status === 'disconnected') {
      whepDelayTimerRef.current = window.setTimeout(() => {
        if (whepStatus.status === 'disconnected') {
          addLog('视频流未连接', 'warning', 'WHEP');
        }
        whepDelayTimerRef.current = null;
      }, 3000);
    }
  }, [whepStatus.status, whepStatus.error, addLog]);

  // 全屏切换函数
  const toggleFullscreen = () => {
    if (!isFullscreen) {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        elem.requestFullscreen().catch(console.error);
      } else if ((elem as any).webkitRequestFullscreen) {
        (elem as any).webkitRequestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if ((document as any).webkitExitFullscreen) {
        (document as any).webkitExitFullscreen();
      }
    }
  };

  // 监听全屏状态变化
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isCurrentlyFullscreen = !!(
        document.fullscreenElement ||
        (document as any).webkitFullscreenElement
      );
      setIsFullscreen(isCurrentlyFullscreen);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    };
  }, []);

  const resolutionWidth = Number(import.meta.env.VITE_STREAM_WIDTH || 1920);
  const resolutionLabel = resolutionWidth === 1280 ? '1280x720' : '1920x1080';
  const resolutionChip = resolutionWidth === 1280 ? '720p' : '1080p';

  return (
    <div style={{
      backgroundColor: '#0a0c10',
      color: '#f1f5f9',
      fontFamily: '"Inter", -apple-system, "Microsoft YaHei", sans-serif',
      overflow: 'hidden',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      margin: 0,
      padding: isFullscreen ? 0 : '16px',
      gap: '12px',
    }}>
      <HeaderBar
        latency={telemetry ? `${telemetry.latency_ms}ms` : '--'}
        temperature={telemetry ? `${telemetry.core_temp_c.toFixed(1)}°C` : '--'}
        battery={telemetry ? `${telemetry.battery_pct.toFixed(1)}%` : '--'}
        onEmergencyStop={triggerEmergencyStop}
        onToggleFullscreen={toggleFullscreen}
        onOpenConfig={() => setShowConfigPanel(true)}
      />

      <main style={{
        flex: 1,
        display: 'flex',
        gap: '0px',
        minHeight: 0,
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '10px',
        overflow: 'hidden',
        background: '#0f1115',
      }}>
        <LeftPanel
          latency={telemetry ? `${telemetry.latency_ms}` : '--'}
          rssi={telemetry ? `${telemetry.rssi_dbm}` : '--'}
          temperature={telemetry ? `${telemetry.core_temp_c.toFixed(1)}` : '--'}
          battery={telemetry ? `${telemetry.battery_pct.toFixed(1)}` : '--'}
          groundspeed={telemetry ? `${telemetry.position.groundspeed.toFixed(2)}` : '--'}
          angularVel={telemetry ? `${(telemetry.attitude.yaw || 0).toFixed(1)}` : '--'}
          resolution={resolutionLabel}
          logs={logs}
        />
        <VideoSection
          isFullscreen={isFullscreen}
          videoRef={videoRef}
          whepStatus={whepStatus}
          isConnected={isConnected}
          resolutionLabel={resolutionChip}
          rssi={telemetry ? `${telemetry.rssi_dbm}` : '--'}
        />
      </main>

      <FooterBar
        systemStatus={systemStatus}
        isConnected={isConnected}
      />

      {/* 配置面板模态框 */}
      {showConfigPanel && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.85)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            width: '800px',
            maxHeight: '90vh',
            overflow: 'auto',
            borderRadius: '8px',
          }}>
            <ConfigPanel />
            <button
              onClick={() => setShowConfigPanel(false)}
              style={{
                marginTop: '16px',
                padding: '12px 24px',
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '6px',
                color: '#fca5a5',
                fontSize: '12px',
                fontWeight: 'bold',
                cursor: 'pointer',
                width: '100%',
              }}
            >
              ✕ 关闭配置
            </button>
          </div>
        </div>
      )}
    </div>
  );
}