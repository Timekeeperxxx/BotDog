# BotDog 实现路线图 (Implementation Plan)

本文档描述若由 AI 代为实现本项目时的代码编写步骤与阶段划分，方便人工或后续迭代参考。

---

## 阶段 0：项目初始化与基础骨架

1. **后端工程骨架**
   - 在仓库根目录创建 `backend/`（或直接在根目录，但推荐独立目录）。
   - 创建基础文件：
     - `backend/main.py`：FastAPI 应用入口。
     - `backend/config.py`：加载 `.env` 与配置矩阵（对应 `09_config_matrix.md`）。
     - `backend/logging_config.py`：Loguru 初始化。
     - `backend/deps.py`：数据库 Session、依赖注入。
   - 实现最小 API：
     - `GET /api/v1/system/health`：返回 `status`、`mavlink_connected`、`uptime`（对应 `06_backend_protocol_schema.md`）。
   - 实现最小 WebSocket：
     - `GET /ws/telemetry`：简单心跳广播假数据，验证前端联通性。

2. **数据库与模型初始化**
   - 使用 SQLAlchemy Async 定义 `models.py`：
     - `InspectionTask`、`TelemetrySnapshot`、`AnomalyEvidence`、`OperationLog`（结构见 `06_backend_protocol_schema.md`）。
   - 创建 `database.py`：
     - Async engine + session 工厂。
     - 初始化 SQLite 文件路径与建表逻辑。

3. **前端工程骨架**
   - 在 `frontend/` 下用 Vite + React + TS 初始化工程。
   - 按 `05_frontend_view_contract.md` 创建基础布局组件：
     - `HeaderBar`、`LeftSidebar`、`VideoHud`、`RightSidebar`、`FooterBar`。
   - 使用 Zustand 建立全局状态：`telemetryStore`、`alertStore`。
   - 建立最小 WebSocket 客户端：
     - 连接 `/ws/telemetry`，打印/展示假数据。

4. **本地运行闭环（MVP Smoke Test）**
   - 按 `10_dev_setup.md` 启动后端和前端。
   - 确认：
     - `/api/v1/system/health` 返回 `healthy`。
     - 前端状态条显示 WebSocket 在线，HUD 看到模拟姿态/电量数据。

---

## 阶段 1：MAVLink 网关与遥测闭环

1. **MAVLink 网关进程/模块**
   - 创建 `backend/mavlink_gateway.py`：
     - 使用 `pymavlink` 监听 `MAVLINK_ENDPOINT`（UDP 14550）。
     - 解析 `HEARTBEAT (#0)`、`GLOBAL_POSITION_INT (#33)`、`ATTITUDE/VFR_HUD`、`NAMED_VALUE_FLOAT (#251)`。
     - 将解析结果转为内部 DTO（`SystemHealthDTO`、`PositionDTO`、`AttitudeDTO` 等）。
   - 设计异步队列：
     - 一个队列用于“遥测广播”（供 WebSocket Telemetry 使用）。
     - 一个队列用于“数据落盘”（供数据库 worker 使用）。

2. **遥测 WebSocket 实现**
   - 在 `backend/ws_routes.py` 中实现 `/ws/telemetry`：
     - 从遥测队列中以 ~15Hz 读取最新样本，转换为 `TELEMETRY_UPDATE` JSON（字段名、Envelope 格式严格对应 `06_backend_protocol_schema.md` 与 `07_mavlink_spec.md`）。
     - 支持多客户端广播。
   - 更新 `system/health`：
     - 根据是否收到最近 `HEARTBEAT` 更新 `mavlink_connected`。

3. **遥测落库与配置接入**
   - 创建 `backend/workers/telemetry_worker.py`：
     - 将遥测队列中数据按降采样策略写入 `telemetry_snapshots`。
   - 引入配置矩阵 `09_config_matrix.md` 中的：
     - `heartbeat_timeout`
     - `telemetry_retention_days`

4. **前端 Telemetry 面板实现**
   - 将 `05_frontend_view_contract.md` 中的字段映射到 Zustand：
     - `attitude`、`position`、`battery`。
   - `HeaderBar` 与 HUD 仪表组件从 store 读取并渲染。

---

## 阶段 2：控制链路调整

2. **后端调整**
   - 维持 `/ws/telemetry`、`/ws/event` 两条广播通道。
   - 控制链路由 FT24 硬件直连，Web 控制不再实现。

3. **前端调整**
   - 保留 WHEP 播放与遥测/事件展示。
   - 移除控制面板与控制指令发送逻辑。

---

## 阶段 3：媒体管线与 WHEP 播放

1. **MediaMTX + FFmpeg**
   - 使用 MediaMTX 提供 WHEP 输出。
   - 使用 FFmpeg 从相机 RTSP 拉流并推送到 MediaMTX 的 `cam` 路径。

2. **前端视频播放**
   - 在 `VideoHud` 组件中通过 WHEP 建立播放连接。
   - 将收到的媒体流挂载到 `<video>`。
   - 接入 `04_ui_prototype.html` 中的全屏/隐藏 UI 状态机。

3. **重连与故障提示**
   - FFmpeg 进程断流自动重连。
   - 前端在 UI 上显示“视频重连中”状态。

---

## 阶段 4：AI 告警与证据链闭环

1. **AI 推理集成**
   - 在边缘端使用 ONNX Runtime 对视频帧进行推理。
   - 当检测到 `T_MAX > thermal_threshold`：
     - 将截图落盘到 `/data/snapshots/...`。
     - 通过 MAVLink `NAMED_VALUE_FLOAT` 报告温度峰值（或边路 HTTP/WS）。

2. **后端告警处理**
   - 在 `mavlink_gateway` 中监听 `T_MAX`。
   - 结合最近 `GLOBAL_POSITION_INT` 与当前 `task_id`：
     - 写入 `anomaly_evidence` 表。
     - 通过 `/ws/event` 广播 `ALERT_RAISED`。

3. **前端抓拍列表与历史页面**
   - 实时列表：
     - 订阅 `/ws/event`，在左侧“实时抓拍”中插入卡片（字段依 `05_frontend_view_contract.md`）。
   - 历史页面：
     - 通过 `GET /api/v1/evidence` 获取指定 `task_id` 的证据列表。

---

## 阶段 5：配置管理与验收测试

1. **配置 API 实现**
   - 根据 `09_config_matrix.md` 与 `06_backend_protocol_schema.md`：
     - 实现 `GET /api/v1/config`（脱敏后的当前配置）。
     - 实现 `POST /api/v1/config`（Admin 角色修改允许热更新的配置）。

2. **前端配置界面（可后置）**
   - 简单表格 + 表单，展示和修改关键参数（如 `thermal_threshold`、`heartbeat_timeout` 等）。

3. **执行 `12_acceptance_tests.md` 中的验收用例**
   - UC-01 ~ UC-05 分别验证：
     - 远程控制流畅度与稳定性。
     - 高温告警与证据链。
     - 链路失效与 Failsafe。
     - 视频延迟与重连机制。
     - 配置修改与限流效果。

4. **非功能性检查**
   - 使用系统监控工具（`htop`、`nvidia-smi` 等）观察 CPU/GPU、内存。
   - 检查日志完整性与磁盘占用（结合配置矩阵中的清理策略）。

---

## 阶段 6：后续迭代与优化（可选）

1. **多进程/微服务拆分**
   - 将 MAVLink 网关、WebSocket Hub、媒体服务拆分为独立进程或容器。

2. **多机协同与 SLAM（对应需求文档 v2.0）**
   - 引入多机 task 管理、多通道 MAVLink。
   - 集成 3D LiDAR 与 SLAM 服务。

3. **云端数据同步**
   - 将 SQLite 升级为 PostgreSQL。
   - 增加批量同步与分布式存储支持。

