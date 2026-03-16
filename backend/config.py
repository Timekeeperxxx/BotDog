"""
配置中心。

职责边界：
- 将 `.env` / 环境变量 与 代码中的默认值解耦；
- 为其他模块提供类型安全的 Settings 对象（单例）。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    全局配置，结合 `.env` 与文档 `09_config_matrix.md`、`06_backend_protocol_schema.md`。

    注意：
    - 仅放“真正需要全局”的配置项，避免无节制膨胀；
    - 可与数据库中的 `config` 表组合，实现“默认值在代码、运行值在 DB”的模式。
    """

    # 基础网络配置
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # MAVLink / 数据库
    MAVLINK_ENDPOINT: str = "udp:127.0.0.1:14550"
    DATABASE_URL: AnyUrl | str = "sqlite+aiosqlite:///./data/botdog.db"

    # 安全配置
    JWT_SECRET: str = "please_change_me"

    # CORS 配置
    CORS_ALLOW_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = False

    # 本地模拟数据 Worker 控制（默认保持当前启用行为）
    SIMULATION_WORKER_ENABLED: bool = True

    # MAVLink 数据源选择（mavlink|simulation）
    # - mavlink: 使用真实 MAVLink 端口
    # - simulation: 使用模拟数据生成器
    MAVLINK_SOURCE: str = "simulation"

    # 配置矩阵中的关键参数（只列当前阶段会用到的）
    HEARTBEAT_TIMEOUT: float = 3.0  # heartbeat_timeout
    TELEMETRY_SAMPLING_HZ: float = 2.0  # 遥测落盘采样频率（Hz）
    TELEMETRY_BROADCAST_HZ: float = 15.0  # 遥测广播频率（Hz）

    # 阶段 4：AI 告警配置
    THERMAL_THRESHOLD: float = 60.0  # 温度阈值（°C）

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / ".env")
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

