"""Unified command display data for text help."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


def _str_width(s: str) -> int:
    """计算字符串在等宽终端的视觉宽度（中文=2，英文=1）。"""
    return sum(2 if re.match(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", c) else 1 for c in s)


def _ljust(s: str, width: int) -> str:
    """左对齐，视觉宽度补空格。"""
    return s + " " * (width - _str_width(s))


CommandGroup = Literal[
    "base",
    "social",
    "meal",
    "profile",
    "sticker",
    "evolution",
    "database",
    "persona",
]


@dataclass
class HelpCommand:
    group: CommandGroup
    command: str
    desc: str
    admin_only: bool = False


HELP_CATALOG_VERSION = 4

GROUP_ORDER: list[CommandGroup] = [
    "base",
    "social",
    "meal",
    "profile",
    "sticker",
    "evolution",
    "database",
    "persona",
]

GROUP_NAMES: dict[CommandGroup, str] = {
    "base": "基础",
    "social": "互动",
    "meal": "群菜单",
    "profile": "画像",
    "sticker": "表情包",
    "evolution": "进化",
    "database": "数据库",
    "persona": "Persona",
}


# ========== 分级帮助系统 ==========

# 一级指令（命令组）定义
TOP_LEVEL_COMMANDS: dict[str, dict] = {
    "af": {"name": "好感度", "desc": "关系温度管理"},
    "san": {"name": "SAN", "desc": "精力值系统"},
    "ps": {"name": "Persona", "desc": "人格生活模拟"},
    "profile": {"name": "画像", "desc": "用户画像管理"},
    "sticker": {"name": "表情包", "desc": "表情包管理"},
    "ev": {"name": "进化", "desc": "人格进化审核"},
    "db": {"name": "数据库", "desc": "数据库统计与管理"},
    "meal": {"name": "菜单", "desc": "群菜单管理"},
    "reflect": {"name": "反思", "desc": "手动触发自我反思"},
    "shut": {"name": "闭嘴", "desc": "让 AI 暂时闭嘴"},
    "今日老婆": {"name": "今日", "desc": "今日老婆功能"},
    "addmeal": {"name": "加菜", "desc": "添加菜品到菜单"},
    "delmeal": {"name": "删菜", "desc": "从菜单删除菜品"},
    "feed": {"name": "喂食", "desc": "喂食角色功能"},
    "kb": {"name": "知识库", "desc": "知识库管理"},
}

# 子命令按指令组分类
SUB_COMMANDS: dict[str, list[tuple]] = {
    "af": [
        ("show", "查看当前好感度", False),
        ("debug", "查看详细好感度", True),
        ("set", "强制设置好感度", True),
    ],
    "san": [
        ("show", "查看当前 SAN 状态", False),
        ("set", "查看或设置 SAN", True),
    ],
    "ps": [
        ("state", "只读当前人格状态", True),
        ("status", "推进后查看人格快照", True),
        ("todo", "查看当前脑内待办", True),
        ("effects", "查看当前状态效果", True),
        ("apply", "应用一次互动影响", True),
        ("tick", "手动推进人格时间", True),
        ("today", "查看今日人格摘要", True),
        ("consolidate", "执行人格日结", True),
        ("think", "手动触发内心独白", True),
    ],
    "profile": [
        ("view", "查看用户画像", False),
        ("create", "创建画像", False),
        ("update", "更新画像", False),
        ("delete", "删除画像", True),
        ("stats", "查看画像统计", True),
    ],
    "sticker": [
        ("list", "查看表情包列表", True),
        ("preview", "预览指定表情包", True),
        ("delete", "删除指定表情包", True),
        ("disable", "禁用指定表情包", True),
        ("enable", "启用指定表情包", True),
        ("clear", "清空全部表情包", True),
        ("stats", "查看表情包统计", True),
        ("sync", "同步本地表情包文件", True),
        ("add", "添加表情包", True),
        ("migrate", "迁移表情包数据", True),
    ],
    "ev": [
        ("review", "查看待审核进化", True),
        ("approve", "批准指定进化", True),
        ("reject", "拒绝指定进化", True),
        ("clear", "清空待审核队列", True),
        ("stats", "查看进化统计", True),
    ],
    "db": [
        ("show", "查看数据库统计", True),
        ("reset", "清空插件数据", True),
        ("rebuild", "删除并重建数据库", True),
        ("confirm", "确认执行危险操作", True),
    ],
    "meal": [
        ("ban", "禁止用户加菜", True),
        ("unban", "解除加菜限制", True),
    ],
}


def _ljust_helper(s: str, width: int) -> str:
    """左对齐，视觉宽度补空格。"""
    return s + " " * (width - _str_width(s))


def format_main_help(is_admin: bool = False) -> str:
    """格式化主帮助：显示所有一级指令（简洁列表）"""
    lines = [
        "【Self-Evolution 指令帮助】",
        "",
    ]

    # 计算最大宽度用于对齐
    max_width = max(_str_width(f"/{cmd}") for cmd in TOP_LEVEL_COMMANDS.keys()) if TOP_LEVEL_COMMANDS else 10

    # 按顺序显示一级指令
    for cmd_name, cmd_info in TOP_LEVEL_COMMANDS.items():
        cmd = f"/{cmd_name}"
        desc = cmd_info["desc"]
        lines.append(f"  {_ljust_helper(cmd, max_width + 2)}  {desc}")

    lines.append("")
    lines.append("💡 输入 /<指令> help 查看详细（如 /af help）")

    return "\n".join(lines)


def format_group_help(group_name: str, is_admin: bool = False) -> str:
    """格式化子帮助：显示指定指令组的所有子命令"""
    name = group_name.lstrip("/").lower()

    # 检查是否为有效的一级指令
    if name not in TOP_LEVEL_COMMANDS:
        return f"[Error] 未找到指令组 '{group_name}'"

    group_info = TOP_LEVEL_COMMANDS[name]
    group_display = f"/{name}"

    # 获取子命令列表
    sub_cmds = SUB_COMMANDS.get(name, [])

    lines = [
        f"【{group_display} {group_info['name']}】",
        "",
    ]

    if not sub_cmds:
        lines.append("  该指令暂无子命令")
    else:
        # 计算最大宽度用于对齐
        max_width = max(_str_width(f"/{name} {sub}") for sub, _, _ in sub_cmds) if sub_cmds else 10

        for sub_cmd, desc, admin_only in sub_cmds:
            full_cmd = f"/{name} {sub_cmd}"
            if admin_only and not is_admin:
                continue  # 非管理员跳过管理员专属命令
            lines.append(f"  {_ljust_helper(full_cmd, max_width + 2)}  {desc}")

    lines.append("")
    lines.append(f"💡 使用 /{name} <子命令> 执行（如 /{name} {sub_cmds[0][0] if sub_cmds else ''}）")

    return "\n".join(lines)


_FULL_CATALOG: list[HelpCommand] = [
    HelpCommand("base", "/se help", "查看指令帮助"),
    HelpCommand("base", "/se version", "查看插件版本"),
    HelpCommand("base", "/reflect", "手动触发一次反思"),
    HelpCommand("base", "/今日老婆", "查看今日老婆"),
    HelpCommand("social", "/af show", "查看当前好感度"),
    HelpCommand("social", "/af debug <用户>", "查看详细好感度（@或ID）", admin_only=True),
    HelpCommand("social", "/af set <用户> <分数>", "强制设置好感度（@或ID）", admin_only=True),
    HelpCommand("social", "/san show", "查看当前 SAN 状态"),
    HelpCommand("social", "/san set [值]", "查看或设置 SAN", admin_only=True),
    HelpCommand("social", "/shut [分钟]", "让 AI 暂时闭嘴", admin_only=True),
    HelpCommand("meal", "/addmeal <菜名>", "添加群菜单菜品"),
    HelpCommand("meal", "/delmeal <菜名>", "删除指定菜品"),
    HelpCommand("meal", "/meal ban <用户>", "禁止某人加菜（@或ID）", admin_only=True),
    HelpCommand("meal", "/meal unban <用户>", "解除加菜限制（@或ID）", admin_only=True),
    HelpCommand("profile", "/profile view [用户ID]", "查看用户画像"),
    HelpCommand("profile", "/profile create [用户ID]", "创建画像"),
    HelpCommand("profile", "/profile update [用户ID]", "更新画像"),
    HelpCommand("profile", "/profile delete <用户ID>", "删除画像", admin_only=True),
    HelpCommand("profile", "/profile stats", "查看画像统计", admin_only=True),
    HelpCommand("sticker", "/sticker list [页码]", "查看表情包列表", admin_only=True),
    HelpCommand("sticker", "/sticker preview <UUID>", "预览指定表情包", admin_only=True),
    HelpCommand("sticker", "/sticker delete <UUID>", "删除指定表情包", admin_only=True),
    HelpCommand("sticker", "/sticker disable <UUID>", "禁用指定表情包", admin_only=True),
    HelpCommand("sticker", "/sticker enable <UUID>", "启用指定表情包", admin_only=True),
    HelpCommand("sticker", "/sticker clear", "清空全部表情包", admin_only=True),
    HelpCommand("sticker", "/sticker stats", "查看表情包统计", admin_only=True),
    HelpCommand("sticker", "/sticker sync", "同步本地表情包文件", admin_only=True),
    HelpCommand("sticker", "/sticker add", "把刚发送的图片加入表情包", admin_only=True),
    HelpCommand("sticker", "/sticker migrate", "迁移旧表情包数据", admin_only=True),
    HelpCommand("evolution", "/ev review [页码]", "查看待审核进化", admin_only=True),
    HelpCommand("evolution", "/ev approve <ID>", "批准指定进化", admin_only=True),
    HelpCommand("evolution", "/ev reject <ID>", "拒绝指定进化", admin_only=True),
    HelpCommand("evolution", "/ev clear", "清空待审核队列", admin_only=True),
    HelpCommand("evolution", "/ev stats [群ID]", "查看进化统计", admin_only=True),
    HelpCommand("database", "/db show", "查看数据库统计", admin_only=True),
    HelpCommand("database", "/db reset", "清空插件数据", admin_only=True),
    HelpCommand("database", "/db rebuild", "删除并重建数据库", admin_only=True),
    HelpCommand("database", "/db confirm", "确认执行危险操作", admin_only=True),
    HelpCommand("persona", "/ps state [群]", "只读当前人格状态", admin_only=True),
    HelpCommand("persona", "/ps status [群]", "推进后查看人格快照", admin_only=True),
    HelpCommand("persona", "/ps tick [quality] [群]", "手动推进人格时间（none/negative/positive）", admin_only=True),
    HelpCommand("persona", "/ps todo [群]", "查看当前脑内待办", admin_only=True),
    HelpCommand("persona", "/ps effects [群]", "查看当前状态效果", admin_only=True),
    HelpCommand(
        "persona", "/ps apply [q] [群]", "应用一次互动影响（q: bad/awkward/normal/good/relief/brief）", admin_only=True
    ),
    HelpCommand("persona", "/ps today [群]", "查看今日人格摘要", admin_only=True),
    HelpCommand("persona", "/ps consolidate [群] [日期]", "执行人格日结（格式: YYYY-MM-DD）", admin_only=True),
    HelpCommand("persona", "/ps think [群]", "手动触发 LLM 生成内心独白", admin_only=True),
]


def get_user_commands() -> list[HelpCommand]:
    return [cmd for cmd in _FULL_CATALOG if not cmd.admin_only]


def get_admin_commands() -> list[HelpCommand]:
    return _FULL_CATALOG


def get_commands_by_group(include_admin: bool = True) -> dict[CommandGroup, list[HelpCommand]]:
    source = _FULL_CATALOG if include_admin else get_user_commands()
    groups: dict[CommandGroup, list[HelpCommand]] = {group: [] for group in GROUP_ORDER}
    for cmd in source:
        groups[cmd.group].append(cmd)
    return groups


def format_text_help(is_admin: bool = False) -> str:
    groups = get_commands_by_group(include_admin=is_admin)
    lines = ["【Self-Evolution 指令帮助】", ""]

    for group in GROUP_ORDER:
        cmds = groups.get(group, [])
        if not cmds:
            continue
        max_cmd_width = max(_str_width(cmd.command) for cmd in cmds)
        lines.append(f"【{GROUP_NAMES[group]}】")
        for cmd in cmds:
            padded = _ljust(cmd.command, max_cmd_width)
            lines.append(f"{padded}  -  {cmd.desc}")
        lines.append("")

    lines.append("发送 /se help 查看帮助")
    return "\n".join(lines).strip()
