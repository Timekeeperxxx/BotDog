"""
SBUS通道变化检测（只打印发生变化的通道）。

功能：
- 按SBUS帧(25字节)对齐解码
- 仅输出发生变化的通道（带时间戳）
- 写入日志文件

使用：
    python backend/sbus_changes_only.py --port COM7 --baud 57600 --mode 8E2 --auto --loose
"""

import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import serial
from loguru import logger

BASE_DIR = Path(__file__).resolve().parents[1]

SBUS_FRAME_SIZE = 25
SBUS_HEADER_BYTE = 0x0F
SBUS_HEADER_INVERTED = 0xF0
SBUS_FOOTERS = {0x00, 0x04}
SBUS_FOOTERS_INVERTED = {0xFF, 0xFB}

MODE_MAP = {
    "8E2": (serial.PARITY_EVEN, serial.STOPBITS_TWO),
    "8E1": (serial.PARITY_EVEN, serial.STOPBITS_ONE),
    "8N2": (serial.PARITY_NONE, serial.STOPBITS_TWO),
    "8N1": (serial.PARITY_NONE, serial.STOPBITS_ONE),
}


def open_serial(
    port: str,
    baudrate: int,
    parity: str,
    stopbits: float,
) -> serial.Serial:
    return serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=parity,
        stopbits=stopbits,
        timeout=0.1,
    )


def decode_sbus_channels(frame: bytes) -> list[int]:
    channels = [0] * 16
    for i in range(16):
        byte_start = 1 + (i * 11 // 8)
        bit_shift = (i * 11) % 8
        if bit_shift <= 5:
            value = (frame[byte_start] >> bit_shift) | (frame[byte_start + 1] << (8 - bit_shift))
        else:
            value = (frame[byte_start] >> bit_shift) | (frame[byte_start + 1] << (8 - bit_shift)) | (frame[byte_start + 2] << (16 - bit_shift))
        channels[i] = value & 0x7FF

    flags = frame[23]
    ch17 = 1 if (flags & 0x01) else 0
    ch18 = 1 if (flags & 0x02) else 0
    channels.extend([ch17, ch18])
    return channels


def main() -> None:
    parser = argparse.ArgumentParser(description="SBUS change-only logger")
    parser.add_argument("--port", default="COM7", help="串口名称")
    parser.add_argument("--baud", type=int, default=57600, help="波特率")
    parser.add_argument("--mode", choices=list(MODE_MAP.keys()), default="8E2", help="串口模式")
    parser.add_argument("--invert", action="store_true", help="软件反相")
    parser.add_argument("--auto", action="store_true", help="自动检测反相（推荐）")
    parser.add_argument("--loose", action="store_true", help="宽松同步：不校验尾字节")
    parser.add_argument("--deadband", type=int, default=2, help="变化阈值（<=此值视为不变）")
    parser.add_argument("--log", default="logs/sbus_changes.log", help="日志路径")
    args = parser.parse_args()

    parity, stopbits = MODE_MAP[args.mode]
    ser = open_serial(args.port, args.baud, parity=parity, stopbits=stopbits)
    logger.info(f"连接到 {args.port} @ {args.baud} ({args.mode})")

    log_path = Path(args.log)
    if not log_path.is_absolute():
        log_path = BASE_DIR / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    buffer = bytearray()
    last_channels: Optional[list[int]] = None

    with open(log_path, "a", encoding="utf-8") as log_fp:
        logger.info(f"变化日志输出到: {log_path}")
        try:
            while True:
                data = ser.read(ser.in_waiting or 64)
                if data:
                    buffer.extend(data)

                    if args.auto:
                        header_bytes = (SBUS_HEADER_BYTE, SBUS_HEADER_INVERTED)
                    else:
                        header_bytes = (SBUS_HEADER_INVERTED if args.invert else SBUS_HEADER_BYTE,)

                    # 先找到连续两帧头(间隔25字节)做同步
                    synced = False
                    while len(buffer) >= SBUS_FRAME_SIZE * 2:
                        start_index = -1
                        for b in header_bytes:
                            idx = buffer.find(bytes([b]))
                            if idx >= 0:
                                start_index = idx if start_index < 0 else min(start_index, idx)

                        if start_index < 0:
                            buffer = buffer[-1:]
                            break

                        if start_index + SBUS_FRAME_SIZE < len(buffer) and buffer[start_index + SBUS_FRAME_SIZE] in header_bytes:
                            if start_index > 0:
                                del buffer[:start_index]
                            synced = True
                            break

                        del buffer[:start_index + 1]

                    if not synced and len(buffer) < SBUS_FRAME_SIZE * 2:
                        continue

                    while len(buffer) >= SBUS_FRAME_SIZE:
                        if buffer[0] not in header_bytes:
                            del buffer[0:1]
                            continue

                        frame = bytes(buffer[:SBUS_FRAME_SIZE])
                        del buffer[:SBUS_FRAME_SIZE]

                        if args.auto:
                            if frame[0] == SBUS_HEADER_INVERTED:
                                frame = bytes((~b) & 0xFF for b in frame)
                        elif args.invert:
                            frame = bytes((~b) & 0xFF for b in frame)

                        channels = decode_sbus_channels(frame)

                        if last_channels is None:
                            last_channels = channels
                            continue

                        changes = []
                        for i, (prev, curr) in enumerate(zip(last_channels, channels), start=1):
                            if abs(curr - prev) > args.deadband:
                                changes.append(f"CH{i}={prev}->{curr}")

                        if changes:
                            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            line = f"{ts} | " + " ".join(changes)
                            print(line)
                            log_fp.write(line + "\n")
                            log_fp.flush()

                        last_channels = channels
                else:
                    time.sleep(0.001)
        except KeyboardInterrupt:
            logger.info("停止")
        finally:
            ser.close()


if __name__ == "__main__":
    main()
