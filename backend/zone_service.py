"""
重点区域判断服务。

职责边界：
- 从数据库 focus_zones 表加载重点区 polygon 到内存
- 提供区内/区外判断接口
- 支持运行时重新加载区域配置

坐标语义：
  polygon 使用图像坐标系（像素），原点为视频帧左上角。
  区域代表"当前视频画面坐标系中的关注区域"，
  不代表真实世界固定方位或地图坐标。
"""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .logging_config import logger


class ZoneService:
    """
    重点区域判断服务。

    使用 OpenCV 的 pointPolygonTest 或几何射线法判断锚点是否在区域内。
    """

    def __init__(self) -> None:
        # 内存中的 polygon 列表，每个元素是 [(x,y), ...]
        self._polygons: list[list[tuple[int, int]]] = []
        self._loaded = False

    async def load_from_db(self, session: AsyncSession) -> None:
        """从数据库加载所有启用的重点区 polygon 到内存。"""
        from .models import FocusZone

        try:
            result = await session.execute(
                select(FocusZone).where(FocusZone.enabled == 1)
            )
            zones = result.scalars().all()
            polys = []
            for zone in zones:
                try:
                    raw = json.loads(zone.polygon_json)
                    # 支持 [[x,y],...] 或 [{"x":..,"y":..},...] 两种格式
                    parsed: list[tuple[int, int]] = []
                    for pt in raw:
                        if isinstance(pt, (list, tuple)) and len(pt) == 2:
                            parsed.append((int(pt[0]), int(pt[1])))
                        elif isinstance(pt, dict):
                            parsed.append((int(pt["x"]), int(pt["y"])))
                    if len(parsed) >= 3:
                        polys.append(parsed)
                        logger.debug(
                            f"[ZoneService] 已加载重点区 '{zone.zone_name}', "
                            f"顶点数={len(parsed)}"
                        )
                    else:
                        logger.warning(
                            f"[ZoneService] 重点区 '{zone.zone_name}' 顶点不足 3 个，跳过"
                        )
                except Exception as exc:
                    logger.error(
                        f"[ZoneService] 解析重点区 zone_id={zone.zone_id} 失败: {exc}"
                    )
            self._polygons = polys
            self._loaded = True
            logger.info(f"[ZoneService] 共加载 {len(self._polygons)} 个重点区")
        except Exception as exc:
            logger.error(f"[ZoneService] 从数据库加载重点区失败: {exc}")

    def load_from_list(self, polygons: list[list[tuple[int, int]]]) -> None:
        """直接从列表加载区域（用于测试或初始化时传入内存数据）。"""
        self._polygons = [p for p in polygons if len(p) >= 3]
        self._loaded = True
        logger.info(f"[ZoneService] 已加载 {len(self._polygons)} 个重点区（内存）")

    def is_inside_zone(self, anchor_point: tuple[int, int]) -> bool:
        """
        判断锚点是否在任意一个启用的重点区内。

        使用射线法（Ray Casting）进行多边形点包含判断。
        锚点推荐使用目标检测框底部中心点 (cx, y2)。

        Args:
            anchor_point: (x, y) 图像像素坐标

        Returns:
            True 若锚点在任意重点区内
        """
        if not self._polygons:
            # 未配置重点区时，返回 True（不限制区域，全画面有效）
            return True

        x, y = anchor_point
        for polygon in self._polygons:
            if _point_in_polygon(x, y, polygon):
                return True
        return False

    @property
    def has_zones(self) -> bool:
        """是否配置了重点区。"""
        return bool(self._polygons)

    @property
    def zone_count(self) -> int:
        return len(self._polygons)


# ─── 几何工具 ────────────────────────────────────────────────────────────────

def _point_in_polygon(x: int, y: int, polygon: list[tuple[int, int]]) -> bool:
    """
    射线法判断点 (x,y) 是否在多边形内。

    时间复杂度 O(n)，n 为多边形顶点数。
    适用于凸多边形和凹多边形。
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


# ─── 全局单例 ────────────────────────────────────────────────────────────────

_zone_service: Optional[ZoneService] = None


def get_zone_service() -> Optional[ZoneService]:
    return _zone_service


def set_zone_service(service: ZoneService) -> None:
    global _zone_service
    _zone_service = service
