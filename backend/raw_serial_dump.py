"""
串口数据抓取并按SBUS帧对齐解码。

功能：
- 从指定串口读取原始字节流
- 按SBUS帧(25字节)对齐
- 输出每帧RAW HEX + 通道分组日志
- 原样写入二进制文件（原始字节流）

默认参数：57600, 8E2（可用参数覆盖）。

使用方法：
    python backend/raw_serial_dump.py
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
    parity: str = serial.PARITY_EVEN,
    stopbits: float = serial.STOPBITS_TWO,
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
    """
    解码SBUS通道（16个模拟 + 2个数字）。
    """
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


def count_sbus_candidates(buf: bytes) -> int:
    count = 0
    limit = len(buf) - SBUS_FRAME_SIZE + 1
    for i in range(limit):
        head = buf[i]
        tail = buf[i + SBUS_FRAME_SIZE - 1]
        if head == SBUS_HEADER_BYTE and tail in SBUS_FOOTERS:
            count += 1
        elif head == SBUS_HEADER_INVERTED and tail in SBUS_FOOTERS_INVERTED:
            count += 1
    return count


def detect_serial_mode(
    port: str,
    baudrate: int,
    timeout_sec: float,
) -> tuple[str, float]:
    best_label = "8E2"
    best_stopbits = serial.STOPBITS_TWO
    best_score = 0

    for label, (parity, stopbits) in MODE_MAP.items():
        try:
            ser = open_serial(port, baudrate, parity=parity, stopbits=stopbits)
        except serial.SerialException:
            continue

        start = time.time()
        buf = bytearray()
        try:
            while time.time() - start < timeout_sec:
                data = ser.read(ser.in_waiting or 128)
                if data:
                    buf.extend(data)
                    if len(buf) > 4096:
                        buf = buf[-4096:]
        finally:
            ser.close()

        score = count_sbus_candidates(buf)
        if score > best_score:
            best_score = score
            best_label = label
            best_stopbits = stopbits

    return best_label, best_stopbits


def dump_raw(
    port: str,
    baudrate: int,
    log_path: str,
    bin_path: str,
    chunk_size: int,
    invert: bool,
    auto_detect: bool,
    auto_mode: bool,
    detect_timeout: float,
    loose: bool,
    args_mode: Optional[str],
    stats: bool,
    sync_headers: int,
) -> None:
    log_file: Optional[object] = None
    bin_file: Optional[object] = None
    ser: Optional[serial.Serial] = None
    buffer = bytearray()

    try:
        parity = serial.PARITY_EVEN
        stopbits = serial.STOPBITS_TWO
        mode_label = "8E2"

        if args_mode:
            mode_label = args_mode
            parity, stopbits = MODE_MAP[mode_label]
            logger.info(f"强制串口模式: {mode_label}")
        elif auto_mode:
            mode_label, stopbits = detect_serial_mode(port, baudrate, detect_timeout)
            parity = MODE_MAP[mode_label][0]
            logger.info(f"自动探测串口模式: {mode_label}")
            if mode_label.startswith("8N"):
                logger.warning("检测到无校验(N). SBUS标准通常为8E2，如仍无帧可能是电平/反相问题")

        ser = open_serial(port, baudrate, parity=parity, stopbits=stopbits)
        logger.info(f"成功连接到 {port} @ {baudrate} baud ({mode_label})")

        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(bin_path).parent.mkdir(parents=True, exist_ok=True)

        log_file = open(log_path, "a", encoding="utf-8")
        bin_file = open(bin_path, "ab")

        logger.info(f"HEX日志输出到: {log_path}")
        logger.info(f"原始二进制输出到: {bin_path}")
        logger.info("开始抓取原始数据，按 Ctrl+C 停止")

        mode = "invert" if invert else "normal"
        if auto_detect:
            mode = "auto"
        logger.info(f"帧同步模式: {mode}")

        last_stat_time = time.time()
        bytes_since = 0
        headers_since = 0
        frames_since = 0
        synced = False
        sync_header: Optional[int] = None

        def try_sync(buf: bytearray, candidates: tuple[int, ...]) -> tuple[Optional[int], Optional[int]]:
            need = SBUS_FRAME_SIZE * sync_headers
            if len(buf) < need:
                return None, None
            max_offset = len(buf) - need
            for offset in range(max_offset + 1):
                b = buf[offset]
                if b not in candidates:
                    continue
                ok = True
                for k in range(1, sync_headers):
                    if buf[offset + k * SBUS_FRAME_SIZE] != b:
                        ok = False
                        break
                if ok:
                    return offset, b
            return None, None

        while True:
            data = ser.read(ser.in_waiting or chunk_size)
            if data:
                bin_file.write(data)
                bin_file.flush()

                bytes_since += len(data)
                headers_since += data.count(bytes([SBUS_HEADER_BYTE])) + data.count(bytes([SBUS_HEADER_INVERTED]))

                buffer.extend(data)

                # 按帧头对齐提取25字节帧
                if auto_detect:
                    header_candidates = (SBUS_HEADER_BYTE, SBUS_HEADER_INVERTED)
                else:
                    header_byte = SBUS_HEADER_INVERTED if invert else SBUS_HEADER_BYTE
                    header_candidates = (header_byte,)

                if not synced:
                    offset, header = try_sync(buffer, header_candidates)
                    if offset is None:
                        if len(buffer) > SBUS_FRAME_SIZE * sync_headers:
                            buffer = buffer[-SBUS_FRAME_SIZE * sync_headers:]
                        continue
                    if offset > 0:
                        del buffer[:offset]
                    sync_header = header
                    synced = True

                while len(buffer) >= SBUS_FRAME_SIZE and synced:
                    if buffer[0] != sync_header:
                        synced = False
                        del buffer[0:1]
                        break

                    frame = bytes(buffer[:SBUS_FRAME_SIZE])
                    del buffer[:SBUS_FRAME_SIZE]

                    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    raw_hex = frame.hex().upper()

                    if sync_header == SBUS_HEADER_INVERTED:
                        frame_for_decode = bytes((~b) & 0xFF for b in frame)
                    else:
                        frame_for_decode = frame

                    channels = decode_sbus_channels(frame_for_decode)

                    def group_line(start_ch: int, values: list[int]) -> str:
                        parts = [f"CH{start_ch + i}={v}" for i, v in enumerate(values)]
                        return " ".join(parts)

                    line_raw = f"{ts} | RAW | {raw_hex}"
                    line_ch = (
                        f"{ts} | CH1-4: {group_line(1, channels[0:4])}"
                        f" | CH5-8: {group_line(5, channels[4:8])}"
                        f" | CH9-12: {group_line(9, channels[8:12])}"
                        f" | CH13-16: {group_line(13, channels[12:16])}"
                        f" | CH17-18: {group_line(17, channels[16:18])}"
                    )

                    log_file.write(line_raw + "\n")
                    log_file.write(line_ch + "\n")
                    print(line_raw)
                    print(line_ch)
                    frames_since += 1
                log_file.flush()
            else:
                time.sleep(0.001)

            if stats and (time.time() - last_stat_time) >= 1.0:
                elapsed = time.time() - last_stat_time
                logger.info(
                    f"stats | bytes/s={bytes_since/elapsed:.0f} | headers/s={headers_since/elapsed:.1f} | frames/s={frames_since/elapsed:.1f}"
                )
                last_stat_time = time.time()
                bytes_since = 0
                headers_since = 0
                frames_since = 0

    except KeyboardInterrupt:
        logger.info("收到中断信号，停止抓取")
    finally:
        if ser and ser.is_open:
            ser.close()
            logger.info("串口已关闭")
        if log_file:
            log_file.close()
        if bin_file:
            bin_file.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Raw serial dump (no protocol parsing).")
    parser.add_argument("--port", default="COM7", help="串口名称，默认 COM7")
    parser.add_argument("--baud", type=int, default=57600, help="波特率，默认 57600")
    parser.add_argument("--mode", choices=list(MODE_MAP.keys()), help="强制串口模式(如 8E2)")
    parser.add_argument("--stats", action="store_true", help="每秒输出统计(字节/帧/帧头频率)")
    parser.add_argument("--sync", type=int, default=3, help="同步时要求连续帧头数量")
    parser.add_argument("--log", default="logs/serial_raw.log", help="HEX日志路径")
    parser.add_argument("--bin", default="logs/serial_raw.bin", help="二进制输出路径")
    parser.add_argument("--chunk", type=int, default=256, help="每次读取的最小字节数")
    parser.add_argument("--invert", action="store_true", help="软件反相（仅当信号为反向电平时启用）")
    parser.add_argument("--auto", action="store_true", help="自动检测反相（推荐用于排障）")
    parser.add_argument("--auto-mode", action="store_true", help="自动探测串口参数(8E2/8E1/8N2/8N1)")
    parser.add_argument("--detect-timeout", type=float, default=1.0, help="自动探测超时秒数")
    parser.add_argument("--loose", action="store_true", help="宽松同步: 只看帧头不校验尾字节")
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.is_absolute():
        log_path = BASE_DIR / log_path

    bin_path = Path(args.bin)
    if not bin_path.is_absolute():
        bin_path = BASE_DIR / bin_path

    dump_raw(
        port=args.port,
        baudrate=args.baud,
        log_path=str(log_path),
        bin_path=str(bin_path),
        chunk_size=args.chunk,
        invert=args.invert,
        auto_detect=args.auto,
        auto_mode=args.auto_mode,
        detect_timeout=args.detect_timeout,
        loose=args.loose,
        args_mode=args.mode,
        stats=args.stats,
        sync_headers=args.sync,
    )


if __name__ == "__main__":
    main()
