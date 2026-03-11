# GStreamer 安装指南

## Windows 安装 GStreamer

### 方法 1：官方安装包（推荐）

1. **下载 GStreamer**
   - 访问：https://gstreamer.freedesktop.org/download/
   - 下载 Windows 安装包（MSI installer）
   - 选择版本：**GStreamer 1.24.x 或更高版本**
   - 下载两个文件：
     - `gstreamer-1.0-msvc-x86_64.msi`（运行时）
     - `gstreamer-1.0-devel-msvc-x86_64.msi`（开发包）

2. **安装步骤**
   - 先安装运行时：`gstreamer-1.0-msvc-x86_64.msi`
   - 再安装开发包：`gstreamer-1.0-devel-msvc-x86_64.msi`
   - 安装路径建议：`C:\gstreamer\1.0\msvc_x86_64`
   - 勾选 "Add to PATH environment variable"

3. **验证安装**
   ```bash
   gst-launch-1.0 --version
   gst-inspect-1.0 --version
   ```

4. **重启终端** 以使 PATH 生效

### 方法 2：使用 winget（如果可用）

```bash
winget install GStreamer.GStreamer
winget install GStreamer.GStreamer.Development
```

### 方法 3：使用 Chocolatey

```bash
choco install gstreamer
choco install gstreamer-devel
```

## 安装后的验证

安装完成后运行：

```bash
# 检查版本
gst-launch-1.0 --version

# 列出所有插件
gst-inspect-1.0 | grep rtp

# 测试基本功能
gst-launch-1.0 videotestsrc ! autovideosink
```

## 常见问题

**Q: 找不到 gst-launch-1.0 命令？**
A: 检查系统 PATH 是否包含 GStreamer bin 目录：
```
C:\gstreamer\1.0\msvc_x86_64\bin
```

**Q: Python 无法导入 Gst？**
A: 安装 Python 绑定：
```bash
.venv/Scripts/pip install PyGObject
```

**Q: 插件缺失？**
A: 确保安装了 "good", "bad", "ugly" 插件包

## BotDog 项目所需的 GStreamer 组件

- rtspsrc（RTSP 源）
- decodebin（自动解码）
- tcpserversink（TCP 服务）
- H.264/H.265 编解码器

确保安装完整版本以获得所有编解码器支持。
