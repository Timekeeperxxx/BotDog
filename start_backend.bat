@echo off
REM BotDog Backend 启动脚本 (Windows)

echo ======================================
echo BotDog Backend 启动中...
echo ======================================
echo.

REM 设置 GStreamer 环境变量
set GST_PLUGIN_PATH=C:\Program Files\gstreamer\1.0\msvc_x86_64\lib\gstreamer-1.0
set GST_PLUGIN_SCANNER=C:\Program Files\gstreamer\1.0\msvc_x86_64\libexec\gstreamer-1.0\gst-plugin-scanner.exe
set PATH=C:\Program Files\gstreamer\1.0\msvc_x86_64\bin;%PATH%

REM 启动后端
.\.venv\Scripts\python.exe run_backend.py

pause
