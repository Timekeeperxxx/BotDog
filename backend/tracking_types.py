"""
自动跟踪类型定义模块。

职责边界：
- 定义跟踪状态枚举 AutoTrackState
- 定义停止原因枚举 TrackStopReason
- 定义控制拥有者枚举 ControlOwner（阶段 2 使用）
- 定义核心数据 DTO：TargetCandidate、ActiveTarget、TrackDecision

不包含任何业务逻辑，仅定义类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─── 状态枚举 ────────────────────────────────────────────────────────────────

class AutoTrackState(str, Enum):
    """自动跟踪状态枚举。"""

    DISABLED = "DISABLED"                    # 功能开关关闭
    IDLE = "IDLE"                            # 等待目标进入
    DETECTING = "DETECTING"                  # 检测到人员，正在稳定命中计数
    TARGET_LOCKED = "TARGET_LOCKED"         # 目标已锁定，准备跟踪
    FOLLOWING = "FOLLOWING"                  # 正在发送跟踪控制命令
    OUT_OF_ZONE_PENDING = "OUT_OF_ZONE_PENDING"  # 目标短时出区，等待确认
    LOST_SHORT = "LOST_SHORT"               # 目标短时丢失，等待恢复
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"     # 人工控制接管
    PAUSED = "PAUSED"                        # 手动暂停
    STOPPED = "STOPPED"                      # 本轮跟踪结束


class TrackStopReason(str, Enum):
    """跟踪停止原因枚举。"""

    OUT_OF_ZONE = "OUT_OF_ZONE"             # 目标出重点区
    TARGET_LOST = "TARGET_LOST"             # 目标丢失超时
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"     # 人工接管
    MISSION_ENDED = "MISSION_ENDED"         # 任务停止
    DISABLED = "DISABLED"                   # 功能关闭
    E_STOP = "E_STOP"                       # 急停
    VIDEO_LOST = "VIDEO_LOST"               # 视频流断开
    MARKED_KNOWN = "MARKED_KNOWN"          # 目标被标记为已知人员


class ControlOwner(str, Enum):
    """控制权拥有者枚举（阶段 2 ControlArbiter 使用）。"""

    NONE = "NONE"
    AUTO_TRACK = "AUTO_TRACK"
    WEB_MANUAL = "WEB_MANUAL"
    REMOTE_CONTROLLER = "REMOTE_CONTROLLER"
    E_STOP = "E_STOP"


# ─── 数据 DTO ────────────────────────────────────────────────────────────────

@dataclass
class TargetCandidate:
    """
    候选跟踪目标。

    阶段 1：track_id 由轻量级帧间 IOU 匹配生成（IOU > 0.4 视为同一目标延续）。
    阶段 2：升级为完整候选目标管理器。
    """

    track_id: int
    bbox: tuple[int, int, int, int]          # (x1, y1, x2, y2) 图像像素坐标
    confidence: float                         # 0.0~1.0
    anchor_point: tuple[int, int]             # 底部中心点 (cx, y2)
    inside_zone: bool
    first_seen_ts: float
    last_seen_ts: float
    stable_hits: int = 0
    is_known_person: bool = False
    manual_ignored: bool = False

    @classmethod
    def from_detection(
        cls,
        track_id: int,
        bbox: tuple[int, int, int, int],
        confidence: float,
        inside_zone: bool,
        ts: float,
    ) -> "TargetCandidate":
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) // 2
        return cls(
            track_id=track_id,
            bbox=bbox,
            confidence=confidence,
            anchor_point=(cx, y2),
            inside_zone=inside_zone,
            first_seen_ts=ts,
            last_seen_ts=ts,
            stable_hits=1,
        )


@dataclass
class ActiveTarget:
    """当前正在跟踪的活跃目标。"""

    track_id: int
    bbox: tuple[int, int, int, int]
    anchor_point: tuple[int, int]
    inside_zone: bool
    locked_at: float
    last_seen_ts: float
    lost_count: int = 0
    follow_started_at: Optional[float] = None
    out_of_zone_count: int = 0              # 连续出区帧计数


@dataclass
class DetectionResult:
    """
    单次检测结果（来自 YOLO detect_many 的输出项）。

    frame_width / frame_height 由调用方填充，用于跟踪决策引擎。
    """

    bbox: tuple[int, int, int, int]         # (x1, y1, x2, y2)
    confidence: float
    class_name: str = "person"


@dataclass
class TrackDecision:
    """跟踪决策结果（follow_decision_engine 输出）。"""

    command: Optional[str] = None           # "left"/"right"/"forward"/"stop"/None
    should_send: bool = False               # 是否实际下发命令（节流/防抖判断后）
    reason: str = ""
