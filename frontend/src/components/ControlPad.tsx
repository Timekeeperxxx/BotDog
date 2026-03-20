/**
 * 机器狗控制面板组件（紧凑两排版）
 *
 * 布局：
 * 行1: [起立] [前进] [下蹲]
 * 行2: [左转] [后退] [右转]
 */

import React, { useCallback } from 'react';
import {
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ChevronsDown,
  ChevronsUp,
} from 'lucide-react';
import { useRobotControl, type RobotCommand } from '../hooks/useRobotControl';

interface ControlPadProps {
  isDisabled?: boolean;
}

interface ButtonConfig {
  cmd: RobotCommand;
  label: string;
  icon: React.ReactNode;
}

const BUTTONS: ButtonConfig[] = [
  { cmd: 'stand',    label: '起立', icon: <ChevronsUp size={14} /> },
  { cmd: 'forward',  label: '前进', icon: <ArrowUp size={14} /> },
  { cmd: 'sit',      label: '下蹲', icon: <ChevronsDown size={14} /> },
  { cmd: 'left',     label: '左转', icon: <ArrowLeft size={14} /> },
  { cmd: 'backward', label: '后退', icon: <ArrowDown size={14} /> },
  { cmd: 'right',    label: '右转', icon: <ArrowRight size={14} /> },
];

export function ControlPad({ isDisabled = false }: ControlPadProps) {
  const { startCommand, stopCommand, isControlling, lastResult, currentCmd } =
    useRobotControl();

  const handlePointerDown = useCallback(
    (cmd: RobotCommand) => (e: React.PointerEvent) => {
      if (isDisabled) return;
      e.currentTarget.setPointerCapture(e.pointerId);
      startCommand(cmd);
    },
    [isDisabled, startCommand]
  );

  const handlePointerUp = useCallback(() => {
    if (isDisabled) return;
    stopCommand();
  }, [isDisabled, stopCommand]);

  const resultColor =
    lastResult?.result === 'ACCEPTED'
      ? 'text-emerald-400'
      : lastResult?.result === 'REJECTED_E_STOP'
      ? 'text-red-400'
      : 'text-yellow-400';

  return (
    <div className={`select-none ${isDisabled ? 'opacity-40 pointer-events-none' : ''}`}>
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[9px] font-black uppercase tracking-widest text-white/40">
          移动控制
        </span>
        {isControlling && (
          <span className="flex items-center gap-1">
            <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[8px] font-black text-emerald-400">{currentCmd}</span>
          </span>
        )}
      </div>

      {/* 两排 3×2 按钮 */}
      <div className="grid grid-cols-3 gap-1">
        {BUTTONS.map(({ cmd, label, icon }) => (
          <button
            key={cmd}
            onPointerDown={handlePointerDown(cmd)}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            onContextMenu={(e) => e.preventDefault()}
            className={`
              flex flex-col items-center justify-center gap-0.5
              h-8 rounded border
              font-black text-[7px] uppercase tracking-tight
              transition-all duration-100 cursor-pointer select-none touch-none
              ${
                currentCmd === cmd && isControlling
                  ? 'bg-white text-black border-white shadow-[0_0_8px_white]'
                  : 'bg-zinc-800/80 text-white/60 border-white/15 hover:border-white/50 hover:text-white'
              }
            `}
          >
            {icon}
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* 状态栏 */}
      <div className="mt-1.5 flex items-center justify-between text-[8px] font-mono">
        {lastResult ? (
          <>
            <span className="text-white/30">{lastResult.ack_cmd}</span>
            <span className={resultColor}>{lastResult.result}</span>
            <span className="text-white/30">{lastResult.latency_ms}ms</span>
          </>
        ) : (
          <span className="text-white/20 w-full text-center">按住按钮控制机器狗</span>
        )}
      </div>
    </div>
  );
}
