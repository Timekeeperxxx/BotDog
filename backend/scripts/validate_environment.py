#!/usr/bin/env python3
"""
环境验证脚本。

职责边界：
- 验证 MediaMTX / FFmpeg 安装
- 验证 Python 依赖
- 检查系统环境
- 报告缺失的依赖
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str]) -> tuple[bool, str, str]:
    """运行命令并返回结果。"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def check_media_tools() -> dict[str, bool]:
    """检查 MediaMTX 与 FFmpeg 安装。"""
    checks = {}

    success, stdout, _ = run_command(["mediamtx", "--version"])
    checks["mediamtx"] = success
    if success:
        print(f"✓ mediamtx: {stdout.strip()}")
    else:
        print("✗ mediamtx: NOT FOUND")

    success, stdout, _ = run_command(["ffmpeg", "-version"])
    checks["ffmpeg"] = success
    if success:
        first_line = stdout.splitlines()[0] if stdout else "ffmpeg"
        print(f"✓ ffmpeg: {first_line}")
    else:
        print("✗ ffmpeg: NOT FOUND")

    return checks


def check_python_dependencies() -> dict[str, bool]:
    """检查 Python 依赖。"""
    checks = {}

    dependencies = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("websockets", "WebSockets"),
        ("pydantic", "Pydantic"),
        ("pydantic_settings", "Pydantic Settings"),
    ]

    for module, name in dependencies:
        try:
            __import__(module)
            checks[module] = True
            print(f"✓ Python package: {name}")
        except ImportError:
            checks[module] = False
            print(f"✗ Python package: {name} (NOT INSTALLED)")

    return checks


def check_system_environment() -> dict[str, bool]:
    """检查系统环境。"""
    checks = {}

    # 检查 Python 版本
    version = sys.version_info
    checks["python_version"] = version >= (3, 10)
    if checks["python_version"]:
        print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    else:
        print(f"✗ Python version: {version.major}.{version.minor}.{version.micro} (需要 >= 3.10)")

    # 检查 /dev/video* 设备（摄像头）
    video_devices = list(Path("/dev").glob("video*"))
    checks["video_devices"] = len(video_devices) > 0
    if checks["video_devices"]:
        print(f"✓ Video devices: {[d.name for d in video_devices]}")
    else:
        print("⚠ Video devices: 未找到摄像头（可选，用于测试）")

    return checks


def main():
    """主函数。"""
    print("=" * 60)
    print("BotDog Phase 4 环境验证")
    print("=" * 60)

    all_checks = {}

    print("\n## 检查 MediaMTX / FFmpeg")
    print("-" * 60)
    all_checks.update(check_media_tools())

    print("\n## 检查 Python 依赖")
    print("-" * 60)
    all_checks.update(check_python_dependencies())

    print("\n## 检查系统环境")
    print("-" * 60)
    all_checks.update(check_system_environment())

    # 汇总结果
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    critical_checks = [
        "mediamtx",
        "ffmpeg",
        "fastapi",
        "uvicorn",
        "websockets",
        "pydantic",
        "pydantic_settings",
        "python_version",
    ]

    failed_critical = [
        check for check in critical_checks
        if not all_checks.get(check, False)
    ]

    if failed_critical:
        print(f"\n✗ 验证失败：{len(failed_critical)} 个关键依赖未安装")
        print("\n缺失的关键依赖：")
        for check in failed_critical:
            print(f"  - {check}")

        print("\n## 安装指南")
        print("\n### MediaMTX / FFmpeg")
        print("- 运行 setup-mediamtx.ps1 与 setup-ffmpeg.ps1")
        print("- 或将 mediamtx.exe / ffmpeg.exe 添加到 PATH")

        print("\n### Python 依赖")
        print("pip install -r requirements.txt")

        return 1
    else:
        print("\n✓ 所有关键依赖已安装，环境验证通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
