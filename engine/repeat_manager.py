"""复读管理模块"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import SelfEvolutionPlugin


@dataclass
class RepeatRecord:
    """复读记录"""
    content_hash: str
    repeated_at: float
    scope_id: str


class RepeatManager:
    """复读管理器

    管理复读的触发判断、冷却控制和历史记录。
    - 概率触发
    - 冷却时间控制
    - 防重复（同一内容不会重复复读）
    """

    def __init__(self, plugin: "SelfEvolutionPlugin"):
        self.plugin = plugin
        self._cooldown_map: dict[str, float] = {}
        self._history: list[RepeatRecord] = []
        self._history_limit = 1000

    def _cleanup_expired_history(self) -> None:
        """清理过期的历史记录"""
        ttl_hours = getattr(self.plugin.cfg, "repeat_history_ttl", 24)
        cutoff = time.time() - (ttl_hours * 3600)
        self._history = [r for r in self._history if r.repeated_at > cutoff]

    def _is_content_repeated_before(self, content: str, scope_id: str) -> bool:
        """检查内容是否在此群复读过"""
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:16]
        for record in self._history:
            if record.content_hash == content_hash and record.scope_id == scope_id:
                return True
        return False

    def _check_cooldown(self, scope_id: str) -> bool:
        """检查冷却时间是否已过"""
        last_time = self._cooldown_map.get(scope_id, 0)
        cooldown_seconds = getattr(self.plugin.cfg, "repeat_cooldown_seconds", 60)
        return (time.time() - last_time) >= cooldown_seconds

    def should_repeat(self, content: str, scope_id: str) -> bool:
        """判断是否应该复读"""
        if not getattr(self.plugin.cfg, "repeat_enabled", False):
            return False

        # 检查群白名单
        target_groups = getattr(self.plugin.cfg, "repeat_target_groups", [])
        if target_groups and scope_id not in target_groups:
            return False

        if not self._check_cooldown(scope_id):
            return False

        if self._is_content_repeated_before(content, scope_id):
            return False

        chance = getattr(self.plugin.cfg, "repeat_chance_percent", 10)
        if random.randint(1, 100) > chance:
            return False

        return True

    def record_repeat(self, content: str, scope_id: str) -> None:
        """记录复读历史"""
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:16]

        self._history.append(RepeatRecord(
            content_hash=content_hash,
            repeated_at=time.time(),
            scope_id=scope_id
        ))

        self._cooldown_map[scope_id] = time.time()

        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit // 2:]

        self._cleanup_expired_history()

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "history_count": len(self._history),
            "cooldown_map_size": len(self._cooldown_map),
            "enabled": getattr(self.plugin.cfg, "repeat_enabled", False),
            "chance_percent": getattr(self.plugin.cfg, "repeat_chance_percent", 10),
            "cooldown_seconds": getattr(self.plugin.cfg, "repeat_cooldown_seconds", 60),
            "target_groups": getattr(self.plugin.cfg, "repeat_target_groups", []),
        }
