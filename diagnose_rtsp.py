#!/usr/bin/env python3
"""
RTSP 连接诊断工具
"""

import subprocess
import sys
import time

print("=" * 80)
print("RTSP 连接诊断")
print("=" * 80)

rtsp_url = "rtsp://192.168.144.25:8554/main.264"

print(f"\n测试 RTSP URL: {rtsp_url}")
print("\n[1] 使用 ffprobe 检查 RTSP 流...")

try:
    # 测试 RTSP 连接
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_streams",
            "-show_format",
            rtsp_url
        ],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode == 0:
        print("\n[成功] RTSP 流可访问！")
        print("\n流信息:")
        print(result.stdout)

        # 解析编码格式
        if "codec_name" in result.stdout:
            if "h264" in result.stdout.lower():
                print("✅ 编码格式: H.264")
            elif "hevc" in result.stdout.lower() or "h265" in result.stdout.lower():
                print("✅ 编码格式: H.265")
            else:
                print("⚠️  未知编码格式")

    else:
        print(f"\n[失败] RTSP 连接失败，代码: {result.returncode}")
        print(f"错误输出:\n{result.stderr}")

except FileNotFoundError:
    print("\n[警告] ffprobe 未安装，尝试使用 GStreamer...")

    # 使用 GStreamer 测试
    print("\n[2] 使用 GStreamer 测试 RTSP 连接...")
    pipeline = f'gst-launch-1.0 -v rtspsrc location={rtsp_url} latency=0 ! decodebin ! fakesink'

    print(f"Pipeline: {pipeline}")
    print("运行 5 秒...\n")

    try:
        proc = subprocess.Popen(
            pipeline,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(5)

        # 检查进程状态
        if proc.poll() is None:
            print("[成功] GStreamer 进程仍在运行，RTSP 连接成功！")
            proc.terminate()
            proc.wait(timeout=3)
        else:
            print(f"[失败] GStreamer 进程退出，代码: {proc.returncode}")

            # 读取错误输出
            try:
                stderr_output = proc.stderr.read()
                if stderr_output:
                    print(f"\n错误输出:\n{stderr_output[-500:]}")
            except:
                pass

    except Exception as e:
        print(f"[错误] GStreamer 测试失败: {e}")

except subprocess.TimeoutExpired:
    print("\n[超时] RTSP 连接超时（10秒）")
    print("可能原因:")
    print("  1. 相机离线")
    print("  2. 网络不通")
    print("  3. RTSP URL 错误")

except Exception as e:
    print(f"\n[错误] 诊断失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("建议的 RTSP URLs:")
print("=" * 80)
print("1. rtsp://192.168.144.25:8554/main.264")
print("2. rtsp://192.168.144.25:8554/h264")
print("3. rtsp://192.168.144.25:8554/stream")
print("4. rtsp://192.168.144.25:554/stream")
print("\n请检查相机的 RTSP URL 是否正确！")
