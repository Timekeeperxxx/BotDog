"""
机器狗适配器模块。

职责边界：
- 定义适配器抽象接口，屏蔽底层设备差异
- SimulatedRobotAdapter：无真实硬件时打印日志（开发 / CI 阶段使用）
- MAVLinkRobotAdapter：预留骨架，真实硬件接入时实现
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from .logging_config import logger


# 合法的动作名集合
VALID_COMMANDS = frozenset({
    "forward",
    "backward",
    "left",
    "right",
    "sit",
    "stand",
    "stop",
})


class BaseRobotAdapter(ABC):
    """
    机器狗适配器基类。

    所有具体适配器必须继承此类并实现 send_command 方法。
    """

    @abstractmethod
    async def send_command(self, cmd: str) -> None:
        """
        向机器狗发送控制命令。

        Args:
            cmd: 动作名（forward/backward/left/right/sit/stand/stop）
        """
        ...

    async def stop(self) -> None:
        """快捷停止方法，供 Watchdog 调用。"""
        await self.send_command("stop")


class SimulatedRobotAdapter(BaseRobotAdapter):
    """
    模拟适配器（无真实硬件时使用）。

    仅打印日志，不发送真实指令。
    后续换真实硬件时，替换为 MAVLinkRobotAdapter，其余代码不变。
    """

    async def send_command(self, cmd: str) -> None:
        """
        模拟执行命令，仅打印日志。

        Args:
            cmd: 动作名
        """
        logger.info(f"[SimulatedAdapter] 执行命令: {cmd}")
        # 模拟指令执行延迟（约 5ms）
        await asyncio.sleep(0.005)


class MAVLinkRobotAdapter(BaseRobotAdapter):
    """
    MAVLink 真实硬件适配器（预留骨架）。

    TODO: 真实硬件接入时实现此类。
    需要注入 MAVLink 连接对象，通过发送相应的 MAVLink 消息控制机器狗。
    """

    def __init__(self, mavlink_connection=None):
        """
        初始化 MAVLink 适配器。

        Args:
            mavlink_connection: pymavlink 连接对象（可选，接入真实硬件时必填）
        """
        self._connection = mavlink_connection

    async def send_command(self, cmd: str) -> None:
        """
        通过 MAVLink 发送控制命令（待实现）。

        Args:
            cmd: 动作名
        """
        # TODO: 实现具体的 MAVLink 命令映射
        # 例如：forward -> SET_POSITION_TARGET_LOCAL_NED with vx=1.0
        logger.warning(f"[MAVLinkAdapter] send_command({cmd}) 尚未实现，已忽略")


# ─── 工厂函数 ────────────────────────────────────────────────────────────────

_adapter: Optional[BaseRobotAdapter] = None


def create_adapter(adapter_type: str = "simulation") -> BaseRobotAdapter:
    """
    创建适配器实例。

    Args:
        adapter_type: 适配器类型（"simulation" | "mavlink"）

    Returns:
        适配器实例
    """
    if adapter_type == "mavlink":
        logger.info("使用 MAVLink 适配器（真实硬件模式）")
        return MAVLinkRobotAdapter()
    else:
        logger.info("使用 SimulatedRobotAdapter（模拟模式）")
        return SimulatedRobotAdapter()


def get_robot_adapter() -> BaseRobotAdapter:
    """获取当前适配器实例（单例）。"""
    global _adapter
    if _adapter is None:
        _adapter = create_adapter("simulation")
    return _adapter


def set_robot_adapter(adapter: BaseRobotAdapter) -> None:
    """注入适配器实例（供测试和初始化时使用）。"""
    global _adapter
    _adapter = adapter
