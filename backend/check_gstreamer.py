#!/usr/bin/env python3
"""
GStreamer 环境检测工具

职责：
- 启动前检测必需的 GStreamer 插件
- 提供清晰的缺失插件提示
- 兼容 Windows/Linux 环境
"""

import subprocess
import sys
import shutil
from pathlib import Path


def check_gstreamer_installation() -> bool:
    """
    检查 GStreamer 是否已安装。

    Returns:
        True 如果 gst-launch-1.0 可用
    """
    try:
        # 先用 shutil.which 检查命令是否存在（兼容 Windows PATH）
        if shutil.which("gst-launch-1.0") is None:
            print("❌ GStreamer 未安装：找不到 gst-launch-1.0 命令")
            return False

        result = subprocess.run(
            ["gst-launch-1.0", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True  # Windows 需要 shell=True 才能找到 PATH 里的命令
        )
        if result.returncode == 0:
            print(f"✅ GStreamer 已安装: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        print("❌ GStreamer 未安装：找不到 gst-launch-1.0 命令")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️ GStreamer 命令超时")
        return False
    except Exception as e:
        print(f"❌ GStreamer 检测失败: {e}")
        return False

    return False


def check_required_plugins() -> list[str]:
    """
    检查必需的 GStreamer 插件。

    Returns:
        缺失的插件列表（空列表表示全部可用）
    """
    required_plugins = [
        ("rtspsrc", "RTSP 源插件"),
        ("decodebin", "自动解码器"),
        ("videoconvert", "视频格式转换"),
        ("tcpserversink", "TCP 服务端"),
    ]

    missing = []

    for plugin, description in required_plugins:
        try:
            # 先检查 gst-inspect-1.0 是否存在
            if shutil.which("gst-inspect-1.0") is None:
                missing.append(f"{plugin} ({description})")
                print(f"❌ 找不到 gst-inspect-1.0 命令")
                break

            # 使用 gst-inspect-1.0 检测插件
            result = subprocess.run(
                ["gst-inspect-1.0", plugin],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True  # Windows 需要 shell=True
            )

            if result.returncode != 0:
                missing.append(f"{plugin} ({description})")
                print(f"❌ 缺少插件: {plugin} - {description}")
            else:
                print(f"✅ 插件可用: {plugin} - {description}")

        except subprocess.TimeoutExpired:
            missing.append(f"{plugin} ({description})")
            print(f"⚠️ 检测插件超时: {plugin}")
        except Exception as e:
            missing.append(f"{plugin} ({description})")
            print(f"❌ 检测插件失败: {plugin} - {e}")

    return missing


def print_installation_guide(missing_plugins: list[str]) -> None:
    """
    打印缺失插件的安装指南。

    Args:
        missing_plugins: 缺失插件列表
    """
    print("\n" + "=" * 80)
    print("🔧 GStreamer 插件安装指南")
    print("=" * 80)

    if sys.platform == "win32":
        print("\nWindows 安装方法：")
        print("1. 访问 https://gstreamer.freedesktop.org/download/")
        print("2. 下载 Windows 安装包（MSI installer）")
        print("3. 安装 GStreamer runtime 和 development 包")
        print("4. 重启终端使 PATH 生效")
    elif sys.platform.startswith("linux"):
        print("\nLinux 安装方法：")
        print("Ubuntu/Debian:")
        print("  sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base")
        print("  sudo apt-get install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad")
        print("  sudo apt-get install gstreamer1.0-plugins-ugly")
        print("\nFedora/RHEL:")
        print("  sudo dnf install gstreamer1-plugins-base-tools")
        print("  sudo dnf install gstreamer1-plugins-good gstreamer1-plugins-bad")
        print("  sudo dnf install gstreamer1-plugins-ugly")
    elif sys.platform == "darwin":
        print("\nmacOS 安装方法：")
        print("  brew install gstreamer")

    print(f"\n缺失的插件 ({len(missing_plugins)}):")
    for plugin in missing_plugins:
        print(f"  - {plugin}")

    print("\n" + "=" * 80)


def main() -> int:
    """
    主入口。

    Returns:
        0 如果所有检查通过，1 如果有错误
    """
    print("\n" + "=" * 80)
    print("🔍 GStreamer 环境检测")
    print("=" * 80 + "\n")

    # 检查 GStreamer 安装
    if not check_gstreamer_installation():
        print_installation_guide(["GStreamer runtime"])
        return 1

    # 检查必需插件
    missing = check_required_plugins()

    if missing:
        print_installation_guide(missing)
        return 1

    print("\n" + "=" * 80)
    print("✅ 所有检查通过，GStreamer 环境就绪")
    print("=" * 80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
