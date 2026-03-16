# 前端环境变量配置迁移

## 变更概述

将前端后端地址与 WHEP 播放地址改为环境变量配置，支持指向 `192.168.144.30:8000` 与 MediaMTX WHEP 地址。

## 新增文件

### 1. `frontend/.env`
生产环境配置，默认指向 `192.168.144.30:8000`

```env
VITE_API_BASE_URL=http://192.168.144.30:8000
VITE_WHEP_URL=http://127.0.0.1:8889/cam/whep
```

### 2. `frontend/.env.local`
本地开发配置，指向 `localhost:8000`

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WHEP_URL=http://127.0.0.1:8889/cam/whep
```

### 3. `frontend/src/config/api.ts`
统一 API 和 WebSocket 地址配置工具

```typescript
getApiBaseUrl()      // 获取后端 API 基础 URL
getWsUrl(path)      // 将 HTTP URL 转换为 WebSocket URL
getApiUrl(path)     // 获取完整的 API URL
```

### 4. （已移除）
前端启动脚本已移除，统一使用 `npm run dev`。

## 修改的文件

### Hooks (8 个文件)

1. **frontend/src/hooks/useBotDogWebSocket.ts**
   - 导入 `getWsUrl`
   - 使用 `getWsUrl('/ws/telemetry')`

2. **frontend/src/hooks/useBotDogWebSocket.ts**
   - 导入 `getWsUrl`
   - 使用 `getWsUrl('/ws/telemetry')`

3. **frontend/src/hooks/useWhepVideo.ts**
   - 使用 `VITE_WHEP_URL` 直连 MediaMTX

4. **frontend/src/hooks/useConfig.ts**
   - 导入 `getApiUrl`
   - 使用 `getApiUrl('')`

### 组件和页面

5. **frontend/src/pages/EvidenceHistory.tsx**
   - 导入 `getApiUrl`
   - 使用 `getApiUrl("/api/v1/evidence")`

## 使用方法

### 开发环境（指向本地后端）

```bash
cd frontend
cp .env.local .env
npm run dev
```

### 生产环境（指向 192.168.144.30）

```bash
cd frontend
npm run dev  # 使用 .env 中的默认配置
```

或者使用启动脚本：

```bash
npm run dev
```

## 环境变量切换

### 切换到不同后端地址

编辑 `frontend/.env`：

```env
# 指向 192.168.144.30
VITE_API_BASE_URL=http://192.168.144.30:8000

# WHEP 播放地址
VITE_WHEP_URL=http://127.0.0.1:8889/cam/whep

# 或指向 localhost
VITE_API_BASE_URL=http://localhost:8000
```

然后重启前端服务器。

## 验证

启动前端后，在浏览器控制台检查网络请求：

```javascript
// 应该看到请求指向 192.168.144.30:8000
// WebSocket 连接指向 ws://192.168.144.30:8000/ws/...
// WHEP 连接指向 http://127.0.0.1:8889/cam/whep
```

## 注意事项

1. **环境变量优先级**：
   - `.env.local` > `.env` > 默认值
   - 生产部署时仅保留 `.env`

2. **前端必须重启**：
   - 修改 `.env` 后必须重启 `npm run dev`
   - 环境变量在构建时读取

3. **WebSocket 自动转换**：
   - `http://` → `ws://`
   - `https://` → `wss://`

4. **WHEP 地址更新**：
   - 修改 `VITE_WHEP_URL` 后需重启前端
