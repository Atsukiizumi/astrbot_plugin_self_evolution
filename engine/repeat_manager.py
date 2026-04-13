"""复读管理模块 - 消息复制式复读"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..main import SelfEvolutionPlugin


ContentType = Literal["text", "image", "sticker"]


@dataclass
class RepeatableContent:
    """可复制的消息内容"""
    content_hash: str
    content_type: ContentType
    scope_id: str
    first_user: str  # 原创者
    repeat_users: set[str] = field(default_factory=set)
    bot_participated: bool = False
    created_at: float = field(default_factory=time.time)


class RepeatManager:
    """消息复制式复读管理器

    机制：
    - 用户 A 发送内容后，记录为"待复制"
    - 用户 B 在无穿插情况下发送相同内容 → Bot 可跟随发送
    - 任何图片/表情包/新文本 → 打断并替换当前内容
    - Bot 参与过后，该内容彻底失效
    - 被原作者重复发送不触发
    """

    def __init__(self, plugin: "SelfEvolutionPlugin"):
        self.plugin = plugin
        self._current: dict[str, RepeatableContent] = {}  # scope_id -> content
        self._bot_participated_content: dict[str, set[str]] = {}  # scope_id -> set of content_hash
        self._max_history = 200

    def _get_content_type(self, is_image: bool, is_sticker: bool) -> ContentType:
        """根据消息标志获取内容类型"""
        if is_sticker:
            return "sticker"
        elif is_image:
            return "image"
        return "text"

    def _make_hash(self, content: str, content_type: ContentType, content_id: str = "") -> str:
        """生成内容 hash"""
        # 图片/表情包使用content_id（URL），文本使用content
        raw = f"{content_type}:{content_id if content_id else content}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]

    def _is_interrupted(self, scope_id: str) -> bool:
        """检查当前内容是否被打断或过期"""
        current = self._current.get(scope_id)
        if not current:
            return False
        # 超过配置时间无任何人复制，自动失效
        expire_minutes = getattr(self.plugin.cfg, "repeat_expire_minutes", 2)
        expire_seconds = expire_minutes * 60
        if time.time() - current.created_at > expire_seconds:
            return True
        return False

    def _clear_current(self, scope_id: str) -> None:
        """清除当前可复制内容"""
        self._current.pop(scope_id, None)

    def _mark_bot_participated(self, scope_id: str, content_hash: str) -> None:
        """标记 Bot 已参与过此内容"""
        if scope_id not in self._bot_participated_content:
            self._bot_participated_content[scope_id] = set()
        self._bot_participated_content[scope_id].add(content_hash)

    def _has_bot_participated(self, scope_id: str, content_hash: str) -> bool:
        """检查 Bot 是否参与过此内容"""
        return content_hash in self._bot_participated_content.get(scope_id, set())

    def _log_debug(self, msg: str) -> None:
        from astrbot.api import logger

        if getattr(self.plugin.cfg, "repeat_debug_enabled", False):
            logger.debug(msg)

    def should_repeat(
        self,
        content: str,
        scope_id: str,
        is_image: bool = False,
        is_sticker: bool = False,
        user_id: str = "",
        content_id: str = "",
    ) -> bool:
        """判断是否应该参与复读

        Args:
            content: 消息文本内容（图片/表情包时为空字符串）
            scope_id: 群号/会话ID
            is_image: 是否为图片消息
            is_sticker: 是否为表情包消息
            user_id: 发送者ID
            content_id: 图片/表情包的唯一标识（URL或file_id），用于区分不同图片
        """
        from astrbot.api import logger

        if not getattr(self.plugin.cfg, "repeat_enabled", False):
            self._log_debug(f"[Repeat] repeat_enabled=False")
            return False

        # 群白名单检查
        target_groups = getattr(self.plugin.cfg, "repeat_target_groups", [])
        if target_groups and scope_id not in target_groups:
            self._log_debug(f"[Repeat] scope not in target_groups")
            return False

        # 内容类型开关检查
        content_type = self._get_content_type(is_image, is_sticker)
        if content_type == "sticker" and not getattr(self.plugin.cfg, "repeat_sticker_enabled", False):
            self._log_debug(f"[Repeat] sticker disabled")
            return False
        if content_type == "image" and not getattr(self.plugin.cfg, "repeat_image_enabled", False):
            self._log_debug(f"[Repeat] image disabled")
            return False

        # 清理已打断的/过期的内容
        current = self._current.get(scope_id)
        if current and self._is_interrupted(scope_id):
            elapsed = time.time() - current.created_at
            self._log_debug(f"[Repeat] Content expired/interrupted, elapsed={elapsed:.1f}s")
            self._clear_current(scope_id)
            current = None

        current = self._current.get(scope_id)
        content_hash = self._make_hash(content, content_type, content_id)

        # 新内容：检查是否与当前可复制内容匹配
        if current:
            # 有人发送了新文本/图片/表情包 → 打断当前
            new_content_type = self._get_content_type(is_image, is_sticker)
            if current.content_type != new_content_type or current.content_hash != content_hash:
                # 类型不同或内容不同 → 打断当前，建立新的
                self._log_debug(
                    f"[Repeat] New content interrupt - "
                    f"old_type={current.content_type}, new_type={new_content_type}, "
                    f"old_hash={current.content_hash[:8]}, new_hash={content_hash[:8]}"
                )
                self._clear_current(scope_id)
                current = None

        if not current:
            # 首次发送，记录但不让 Bot 参与
            self._current[scope_id] = RepeatableContent(
                content_hash=content_hash,
                content_type=content_type,
                scope_id=scope_id,
                first_user=user_id,
                repeat_users={user_id},
            )
            self._log_debug(f"[Repeat] New content recorded, type={content_type}, first_user={user_id}, hash={content_hash[:8]}")
            return False

        # ===== 有待复制内容 =====
        self._log_debug(
            f"[Repeat] Checking repeat - current: type={current.content_type}, "
            f"first_user={current.first_user}, repeat_users={current.repeat_users}, "
            f"bot_participated={current.bot_participated}, hash={current.content_hash[:8]}"
        )

        # 1. Bot 已参与过 → 不参与
        if self._has_bot_participated(scope_id, content_hash):
            self._log_debug(f"[Repeat] Bot already participated, hash={content_hash[:8]}")
            return False

        # 2. 发送者是原创者 → 不参与
        if user_id == current.first_user:
            self._log_debug(f"[Repeat] sender={user_id} is first_user={current.first_user}")
            return False

        # 3. 发送者已参与过 → 不参与
        if user_id in current.repeat_users:
            self._log_debug(f"[Repeat] sender={user_id} already in repeat_users={current.repeat_users}")
            return False

        # 4. 通过所有检查 → Bot 可以参与
        self._log_debug(f"[Repeat] Should repeat: content={content[:20] if content else '(image/sticker)'}")
        return True

    def on_bot_repeated(
        self,
        content: str,
        scope_id: str,
        is_image: bool = False,
        is_sticker: bool = False,
        content_id: str = "",
    ) -> None:
        """Bot 实际参与复读后调用，标记该内容 Bot 已参与"""
        content_type = self._get_content_type(is_image, is_sticker)
        content_hash = self._make_hash(content, content_type, content_id)
        self._mark_bot_participated(scope_id, content_hash)

        # 同时清除当前可复制内容，避免重复触发
        self._clear_current(scope_id)

    def record_user_repeat(
        self,
        content: str,
        scope_id: str,
        is_image: bool = False,
        is_sticker: bool = False,
        user_id: str = "",
        content_id: str = "",
    ) -> None:
        """记录用户复制（用于更新用户列表）"""
        if not scope_id or not user_id:
            return

        content_type = self._get_content_type(is_image, is_sticker)
        content_hash = self._make_hash(content, content_type, content_id)

        current = self._current.get(scope_id)
        if current and current.content_hash == content_hash:
            current.repeat_users.add(user_id)

    def handle_interrupted(self, scope_id: str) -> None:
        """处理打断事件（当检测到新内容时调用）"""
        self._clear_current(scope_id)

    def get_random_delay(self) -> float:
        """获取随机延迟秒数"""
        min_delay = getattr(self.plugin.cfg, "repeat_delay_seconds_min", 3)
        max_delay = getattr(self.plugin.cfg, "repeat_delay_seconds_max", 15)
        return random.uniform(min_delay, max_delay)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "current_contents": len(self._current),
            "bot_participated_count": sum(
                len(s) for s in self._bot_participated_content.values()
            ),
            "enabled": getattr(self.plugin.cfg, "repeat_enabled", False),
            "chance_percent": getattr(self.plugin.cfg, "repeat_chance_percent", 10),
        }