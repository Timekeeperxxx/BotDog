# BotDog 环境配置完成 ✅

## 环境信息
- **Python**: 3.12.x (虚拟环境: `.venv`)
- **Node.js**: npm 11.9.0
- **数据库**: SQLite (`data/botdog.db`)

## 启动服务

### 方法 1：使用提供的启动脚本（推荐）

**后端：**
```bash
.venv/Scripts/python.exe run_backend.py
```

**前端（新开终端）：**
```bash
cd frontend
npm run dev
```

### 方法 2：直接使用 uvicorn

**后端：**
```bash
.venv/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端：**
```bash
cd frontend
npm run dev
```

## 访问地址

- **前端界面**: http://localhost:5174
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **交互式 API**: http://localhost:8000/redoc

## 配置说明

默认配置位于 `backend/config.py`，可通过 `.env` 文件覆盖：

```bash
# .env 文件示例
MAVLINK_ENDPOINT=udp:127.0.0.1:14550
DATABASE_URL=sqlite+aiosqlite:///./data/botdog.db
SIMULATION_WORKER_ENABLED=true
MAVLINK_SOURCE=simulation
```

## 依赖说明

**Python 依赖已安装：**
- FastAPI + Uvicorn（Web 框架）
- SQLAlchemy + aiosqlite（数据库）
- WebSocket（实时通信）
- OpenCV + NumPy（视频处理）
- PyMAVLink（机器人协议）
- MediaMTX + FFmpeg（视频推流/播放）

**前端依赖已安装：**
- React 18 + TypeScript
- Vite（构建工具）

**✅ WHEP 视频链路已启用**
MediaMTX + FFmpeg 推流与 WHEP 播放测试通过。

## 故障排除

**1. 端口被占用**
```bash
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :5174

# 更改端口
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

**2. 数据库错误**
```bash
# 重新初始化数据库
rm data/botdog.db
.venv/Scripts/python.exe init_db.py
```

**3. 虚拟环境未激活**
确保使用完整路径：`.venv/Scripts/python.exe`

## 下一步

1. 启动后端服务
2. 启动前端服务
3. 浏览器访问 http://localhost:5174
4. 开始使用 BotDog 控制系统！

---
**配置时间**: 2026-03-10
**状态**: ✅ 环境就绪，WHEP 视频链路已启用
**后端测试**: ✅ 启动成功（http://0.0.0.0:8000）
