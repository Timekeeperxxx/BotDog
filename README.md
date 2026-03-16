# BotDog 机器狗控制系统

![Version](https://img.shields.io/badge/version-5.0-blue)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 项目简介

BotDog 是一个完整的**四足机器狗远程控制系统**，提供实时控制、遥测监控、AI 告警和可视化界面。

### 核心功能

- ✅ **遥测监控** - 实时姿态、位置、温度、电池
- ✅ **AI 告警** - 温度异常自动检测和告警
- ✅ **配置管理** - 可视化配置界面，13 个配置项
- ✅ **视频流** - MediaMTX + WHEP 低延迟视频传输
- ✅ **事件系统** - 实时事件推送和历史记录

### 技术栈

**后端**:
- Python 3.12+
- FastAPI（Web 框架）
- SQLAlchemy（ORM）
- WebSocket（实时通信）
- MediaMTX + WHEP（视频流）
- MAVLink（机器人通信协议）

**前端**:
- React 18
- TypeScript
- Vite（构建工具）
- WebSocket（实时数据）
- MediaMTX + WHEP（视频流）

---

## 快速开始

### 1. 环境要求

```bash
# Python 3.12+
python --version

# Node.js 18+
node --version
npm --version
```

### 2. 安装依赖

```bash
# 创建并激活 Python 虚拟环境（首次运行）
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或者在 Windows 上使用: .venv\Scripts\activate

# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 3. 启动服务

```bash
# 激活虚拟环境（如果尚未激活）
source .venv/bin/activate  # Linux/Mac

# 后端（终端 1）- 从项目根目录启动
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 或者进入 backend 目录启动
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000


#win后端启动方案：
.venv/Scripts/python.exe run_backend.py

# 前端（终端 2）- 新开一个终端
cd frontend
npm run dev
```

> **重要**：
> - 后端必须使用 `--host 0.0.0.0` 监听所有网卡，否则外部设备无法连接
> - 生产环境可以去掉 `--reload` 参数，提高性能
> - 如果端口被占用，可以使用 `--port 8001` 等其他端口

### 4. 访问界面

打开浏览器访问: `http://localhost:5174` 或 `http://YOUR_IP:5174`

---

## 视频流获取指南

### 视频流架构

```
┌─────────────┐   RTSP(H.265)   ┌─────────────┐   RTSP publish  ┌─────────────┐
│  相机 RTSP   │ ──────────────> │   FFmpeg     │ ──────────────> │  MediaMTX   │
│ (H.265)      │   554/8554     │  转码 H.264  │                 │  WHEP 输出  │
└─────────────┘                  └─────────────┘                 └─────┬──────┘
                                                                       │
                                                                       ▼
                                                               ┌─────────────┐
                                                               │  浏览器播放  │
                                                               │  (WHEP)     │
                                                               └─────────────┘
```

### 本机低延迟播放（推荐）

**步骤**：
1. 运行 MediaMTX：`run-pipeline.cmd`
2. 运行 FFmpeg 推流：`ffmpeg-supervisor.cmd`
3. 打开静态页面 `http://127.0.0.1:8090/index.html` 或前端 `npm run dev`

**默认配置**：
- 相机 RTSP：`CAMERA_RTSP_URL=rtsp://192.168.144.25:8554/main.264`
- MediaMTX RTSP：`rtsp://127.0.0.1:8554/cam`
- WHEP：`http://127.0.0.1:8889/cam/whep`

### FFmpeg 推流命令（手动）

```bash
ffmpeg -rtsp_transport tcp -i rtsp://<CAMERA_IP>:8554/main.264 \
  -fflags nobuffer -flags low_delay -an \
  -c:v libx264 -preset ultrafast -tune zerolatency -g 30 -keyint_min 30 \
  -f rtsp rtsp://127.0.0.1:8554/cam
```

### WHEP 测试页

- `web/index.html` 用于快速验证 WHEP 播放。
- 可在输入框中修改 WHEP URL。

### 故障排查

**问题 1：WHEP 无法连接**
- 确认 MediaMTX 正在运行并监听 8889
- 检查浏览器控制台是否有 CORS/ICE 错误
- 确认 `VITE_WHEP_URL` 与 WHEP 地址一致

**问题 2：没有视频流**
- 确认 FFmpeg 进程运行中
- 相机 RTSP 地址是否可达
- MediaMTX 日志中应看到 `path cam` 有发布者

**问题 3：延迟过高**
- 降低 FFmpeg 输出分辨率/码率
- 检查网络带宽与丢包情况
- 减少相机编码 GOP 间隔（如可配置）

---

## 控制方式

控制链路已切换为 FT24 硬件直连，Web 控制面板已下线。

---

## 配置管理

### 配置界面

点击顶部状态栏的 **"⚙️ 配置"** 按钮打开配置界面。

### 配置类别

**后端配置** (4 项):
- `thermal_threshold` - 高温告警阈值
- `heartbeat_timeout` - 心跳超时
- `ws_max_clients_per_ip` - WebSocket 连接限制
- `video_watchdog_timeout_s` - 视频看门狗超时

**前端配置** (4 项):
- `ui_alert_ack_timeout_s` - 告警确认超时
- `telemetry_display_hz` - 遥测显示刷新率
- `ui_lang` - 界面语言
- `ui_theme` - UI 主题

**存储配置** (3 项):
- `snapshot_retention_days` - 快照保留天数
- `max_snapshot_disk_usage_gb` - 快照最大占用
- `telemetry_retention_days` - 遥测数据保留天数

---

## 系统架构

```
┌───────────────────────────────────────────────────────┐
│                       浏览器界面                        │
│  ┌────────────────────────────────────────────────┐   │
│  │  HeaderBar  │  VideoSection  │  SnapshotList │   │
│  └────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
                           │
                  WebSocket + WHEP
                           │
┌───────────────────────────────────────────────────────┐
│                    FastAPI 后端                      │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────┐ │
│  │  WebSocket   │  │ AlertService  │  │MAVLink  │ │
│  │   Handler     │  │ConfigService  │  │ Gateway │ │
│  └───────────────┘  └───────────────┘  └─────────┘ │
│  ┌───────────────────────────────────────────────┐   │
│  │                Database (SQLite)             │   │
│  └───────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
                           │
                   MAVLink / Serial
                           │
┌───────────────────────────────────────────────────────┐
│              机器狗硬件（摄像头、MAVLink 设备）      │
└───────────────────────────────────────────────────────┘
```

```
┌─────────────┐   RTSP(H.265)   ┌─────────────┐   RTSP publish  ┌─────────────┐
│  相机 RTSP   │ ──────────────> │   FFmpeg     │ ──────────────> │  MediaMTX   │
│ (H.265)      │                 │  转码 H.264  │                 │  WHEP 输出  │
└─────────────┘                  └─────────────┘                 └─────┬──────┘
                                                                      │
                                                                      ▼
                                                              ┌─────────────┐
                                                              │  浏览器播放  │
                                                              │  (WHEP)     │
                                                              └─────────────┘
```

---

## 验收测试

```bash
# 运行所有验收测试（UC-01 到 UC-05）
python acceptance_test.py
```

### 测试覆盖

- ✅ UC-01: 系统健康检查
- ✅ UC-02: 遥测 WebSocket 连接
- ✅ UC-03: 事件 WebSocket 连接
- ✅ UC-04: 配置管理 API
- ✅ UC-05: 告警系统功能

**当前通过率**: 100% (5/5)

---

## 文档

详细文档请查看 [docs/](docs/) 目录：

### 核心文档
- [需求与用例](docs/01_requirements_use_cases.md)
- [实施计划](docs/13_implementation_plan.md)
- [开发环境搭建](docs/10_dev_setup.md)

### 技术规范
- [前端视图契约](docs/05_frontend_view_contract.md)
- [后端协议规范](docs/06_backend_protocol_schema.md)
- [MAVLink 规范](docs/07_mavlink_spec.md)

### 最新功能
- [配置管理界面](docs/23_config_panel_implementation.md)

### 部署指南
- [Git 推送指南](docs/25_git_push_guide.md)

---

## 🔧 开发命令

> **提示**: 所有后端命令都需要先激活虚拟环境：
> ```bash
> source .venv/bin/activate  # Linux/Mac
> .venv\Scripts\activate     # Windows
> ```

### 后端

```bash
# 开发模式（热重载）
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# 初始化配置数据库
python init_config.py

# 运行单元测试
pytest tests/
```

### 前端

```bash
# 开发模式
cd frontend
npm run dev

# 生产构建
npm run build

# 预览生产构建
npm run preview
```

### 数据库

```bash
# 初始化数据库表
python init_config.py

# 清理数据库（谨慎使用）
rm -f data/botdog.db
```

---

## 📁 项目结构

```
BotDog/
├── backend/              # FastAPI 后端
│   ├── main.py          # 主应用入口
│   ├── database.py      # 数据库连接
│   ├── models*.py       # SQLAlchemy 模型
│   ├── services_*.py    # 业务服务层
│   └── ws_*.py          # WebSocket 处理器
│
├── frontend/            # React 前端
│   ├── src/
│   │   ├── components/   # React 组件
│   │   ├── hooks/        # React Hooks
│   │   ├── types/        # TypeScript 类型
│   │   └── utils/        # 工具函数
│   └── package.json
│
├── docs/                # 项目文档
├── tests/               # 后端测试
├── data/                # 数据库文件
├── acceptance_test.py   # 验收测试
└── requirements.txt     # Python 依赖
```

---

## 🚢 部署

### 前置条件

1. **机器狗端需要**:
   - MAVLink 设备（串口或 UDP 连接）
   - 摄像头设备（/dev/video0）
   - Python 3.10+ 环境
   - GStreamer 库

2. **操作端需要**:
   - 现代浏览器（Chrome/Firefox/Edge）
   - 网络连接到机器狗
   - 游戏手柄（可选）

详细部署步骤请参考: [docs/31_startup_guide.md](docs/31_startup_guide.md)

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 提交规范

- 遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范
- 添加测试覆盖新功能
- 更新相关文档

---

## 📄 许可证

MIT License

---

## 作者

- **开发者**: Claude Code + Human collaborator
- **项目**: BotDog 机器狗控制系统
- **版本**: v5.0

---

## 致谢

感谢所有开源项目的贡献者：
- FastAPI
- React
- MediaMTX
- FFmpeg
- MAVLink

---

**状态**: ✅ 生产就绪
**最后更新**: 2026-03-06
**仓库**: https://github.com/Timekeeperxxx/BotDog
