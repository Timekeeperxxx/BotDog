"""
多目标候选集管理器。

职责边界：
- 维护当前帧的所有候选目标列表
- 选定最优跟踪目标（当前目标保持优先硬规则）
- 提供目标切换判定（新目标须 2 倍以上评分才可抢占）
- 清理过期候选目标

阶段 2 新增，替代 AutoTrackService 中的简单单目标逻辑。
track_id 仍使用 bbox IOU 帧间匹配（阶段 2 扩展至多目标管理）。
阶段 3 可升级为完整 ReID 方案。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .tracking_types import TargetCandidate, ActiveTarget
from .logging_config import logger


# 目标切换所需的最低评分倍数（新目标须超过当前目标此倍数才可抢占）
DEFAULT_SWITCH_SCORE_MULTIPLIER = 2.0

# 候选目标在帧间 IOU 匹配后的最小 IOU 阈值
CANDIDATE_IOU_THRESHOLD = 0.3


@dataclass
class ScoredCandidate:
    """带有优先级评分的候选目标。"""

    candidate: TargetCandidate
    score: float
    is_current: bool = False   # 是否为当前活跃目标（保持优先硬规则）


class TargetManager:
    """
    多目标候选集管理器。

    评分规则（优先级从高到低）：
    1. 当前已锁定目标保持优先（硬规则，不可被普通候选抢占）
    2. 位于重点区核心区域（inside_zone=True）
    3. 视觉近似距离更近（锚点 anchor_y 更大 + bbox 面积更大）
    4. 置信度更高
    5. 首次进入时间更早

    目标切换条件（满足其一）：
    - 当前目标丢失 / 出区终止
    - 当前目标被标记为已知
    - 新目标评分 >= switch_score_multiplier 倍当前目标评分
    """

    def __init__(
        self,
        frame_width: int,
        frame_height: int,
        switch_score_multiplier: float = DEFAULT_SWITCH_SCORE_MULTIPLIER,
        max_lost_frames: int = 30,
    ) -> None:
        self._frame_width = frame_width
        self._frame_height = frame_height
        self._switch_score_multiplier = switch_score_multiplier
        self._max_lost_frames = max_lost_frames

        # 候选目标池（按 track_id 索引）
        self._candidates: dict[int, TargetCandidate] = {}

        # 当前活跃目标 track_id（None 表示无活跃目标）
        self._active_track_id: Optional[int] = None

        # 全局 track_id 计数器（帧间 IOU 匹配分配）
        self._next_track_id: int = 0

    # ─── 公共接口 ────────────────────────────────────────────────────────────

    def update(
        self,
        detections: list[tuple[tuple[int, int, int, int], float, str]],  # (bbox, conf, class_name)
        inside_zone_fn,  # callable: anchor_point -> bool
        ts: Optional[float] = None,
    ) -> None:
        """
        用当前帧的检测结果更新候选目标池。

        Args:
            detections: [(bbox, confidence, class_name), ...]
            inside_zone_fn: 判断锚点是否在区域内的函数
            ts: 当前时间戳（None 则用 time.monotonic()）
        """
        if ts is None:
            ts = time.monotonic()

        # 过滤只要 person
        person_dets = [(b, c) for b, c, cls in detections if cls == "person"]

        # 帧间 IOU 匹配：将检测框与现有候选匹配
        matched_ids: set[int] = set()
        new_dets: list[tuple[tuple[int, int, int, int], float]] = []

        for bbox, conf in person_dets:
            best_id, best_iou = self._find_best_match(bbox)
            if best_id is not None and best_iou >= CANDIDATE_IOU_THRESHOLD:
                # 匹配到已有候选，更新
                cand = self._candidates[best_id]
                cand.bbox = bbox
                cand.confidence = conf
                x1, y1, x2, y2 = bbox
                anchor = ((x1 + x2) // 2, y2)
                cand.anchor_point = anchor
                cand.inside_zone = inside_zone_fn(anchor)
                cand.last_seen_ts = ts
                cand.stable_hits += 1
                matched_ids.add(best_id)
            else:
                # 未匹配，记录为新候选
                new_dets.append((bbox, conf))

        # 为未匹配的检测创建新候选
        for bbox, conf in new_dets:
            track_id = self._next_track_id
            self._next_track_id += 1
            x1, y1, x2, y2 = bbox
            anchor = ((x1 + x2) // 2, y2)
            self._candidates[track_id] = TargetCandidate(
                track_id=track_id,
                bbox=bbox,
                confidence=conf,
                anchor_point=anchor,
                inside_zone=inside_zone_fn(anchor),
                first_seen_ts=ts,
                last_seen_ts=ts,
                stable_hits=1,
            )

        # 更新未匹配到的候选（未见帧数 +1，但这里通过 last_seen_ts 来判断）
        # 不直接删除，由 prune_stale() 处理

    def select_best_target(
        self, stable_hits_threshold: int = 3
    ) -> Optional[TargetCandidate]:
        """
        从候选池选择最优跟踪目标。

        硬规则：当前活跃目标保持优先，除非满足切换条件。

        Returns:
            最优候选目标，或 None（无合适候选时）
        """
        now = time.monotonic()
        eligible = [
            c for c in self._candidates.values()
            if c.stable_hits >= stable_hits_threshold
            and c.inside_zone
            and not c.is_known_person
            and not c.manual_ignored
            and (now - c.last_seen_ts) < 1.0  # 1 秒内见过
        ]

        if not eligible:
            return None

        # 计算评分
        scored = [
            ScoredCandidate(
                candidate=c,
                score=self._compute_score(c),
                is_current=(c.track_id == self._active_track_id),
            )
            for c in eligible
        ]

        # 找当前目标
        current = next((s for s in scored if s.is_current), None)

        if current is not None:
            # 当前目标仍在候选列表中，检查是否有候选满足抢占条件
            for s in scored:
                if not s.is_current:
                    if s.score >= current.score * self._switch_score_multiplier:
                        logger.info(
                            f"[TargetManager] 目标切换：track_id {self._active_track_id} "
                            f"→ {s.candidate.track_id}（评分倍数={s.score / current.score:.1f}）"
                        )
                        self._active_track_id = s.candidate.track_id
                        return s.candidate
            # 没有候选满足抢占条件，保持当前目标
            return current.candidate
        else:
            # 当前目标不在候选中（丢失/出区），选评分最高的
            best = max(scored, key=lambda s: s.score)
            self._active_track_id = best.candidate.track_id
            logger.info(
                f"[TargetManager] 选定新目标 track_id={best.candidate.track_id} "
                f"score={best.score:.2f}"
            )
            return best.candidate

    def prune_stale(self, max_age_seconds: float = 2.0) -> None:
        """删除超过 max_age_seconds 未见的候选目标。"""
        now = time.monotonic()
        stale = [
            tid for tid, c in self._candidates.items()
            if (now - c.last_seen_ts) > max_age_seconds
        ]
        for tid in stale:
            del self._candidates[tid]
        if stale:
            logger.debug(f"[TargetManager] 清理过期候选: {stale}")

    def mark_known(self, track_id: int) -> None:
        """将指定 track_id 标记为已知人员（不再参与目标选择）。"""
        if track_id in self._candidates:
            self._candidates[track_id].is_known_person = True
        if self._active_track_id == track_id:
            self._active_track_id = None
            logger.info(f"[TargetManager] track_id={track_id} 标记为已知，清除活跃目标")

    def mark_ignored(self, track_id: int) -> None:
        """人工忽略指定目标。"""
        if track_id in self._candidates:
            self._candidates[track_id].manual_ignored = True

    def clear_active(self) -> None:
        """清除当前活跃目标（跟踪停止时调用）。"""
        self._active_track_id = None

    def reset(self) -> None:
        """重置所有状态（任务结束时调用）。"""
        self._candidates.clear()
        self._active_track_id = None

    @property
    def active_track_id(self) -> Optional[int]:
        return self._active_track_id

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    def get_candidate(self, track_id: int) -> Optional[TargetCandidate]:
        return self._candidates.get(track_id)

    # ─── 内部工具 ────────────────────────────────────────────────────────────

    def _compute_score(self, c: TargetCandidate) -> float:
        """
        计算候选目标的优先级评分。

        评分维度（归一化到 0~1 再加权）：
        - 区内加分：+10（确保区内目标优先于区外）
        - 视觉近似距离：锚点 anchor_y / frame_height（越靠下越近，0~1）
        - bbox 面积比：bbox_area / frame_area（越大越近，0~1）
        - 置信度：0~1
        - 首次进入时间奖励：越早越高（0~1 归一化到 0.5 范围）
        """
        x1, y1, x2, y2 = c.bbox
        area = (x2 - x1) * (y2 - y1)
        frame_area = self._frame_width * self._frame_height
        area_ratio = area / frame_area if frame_area > 0 else 0.0

        anchor_y_normalized = c.anchor_point[1] / self._frame_height

        # 首次进入时间（越早越好，最多加 0.3 分）
        age = time.monotonic() - c.first_seen_ts
        age_bonus = min(0.3, age * 0.01)  # 每秒 0.01，最多 0.3

        score = (
            (10.0 if c.inside_zone else 0.0)   # 区内强优先
            + anchor_y_normalized * 2.0          # 视觉距离（锚点越低越近）
            + area_ratio * 3.0                   # bbox 面积（越大越近）
            + c.confidence * 1.0                 # 置信度
            + age_bonus                          # 首次进入时间奖励
        )
        return score

    def _find_best_match(
        self,
        bbox: tuple[int, int, int, int],
    ) -> tuple[Optional[int], float]:
        """在候选池中找与 bbox IOU 最高的候选，返回 (track_id, iou)。"""
        best_id = None
        best_iou = 0.0
        for tid, cand in self._candidates.items():
            iou = _calc_iou(bbox, cand.bbox)
            if iou > best_iou:
                best_iou = iou
                best_id = tid
        return best_id, best_iou


# ─── 几何工具 ────────────────────────────────────────────────────────────────

def _calc_iou(
    bbox_a: tuple[int, int, int, int],
    bbox_b: tuple[int, int, int, int],
) -> float:
    ax1, ay1, ax2, ay2 = bbox_a
    bx1, by1, bx2, by2 = bbox_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0
