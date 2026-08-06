"""管理员 /dmr 配置命令：解析、类型转换、敏感字段拦截、配置应用与帮助文本。

命令对配置的修改仅运行时生效（不写 config.toml、无 override 文件），
重启后恢复 WebUI / config.toml 中的配置值。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# 敏感字段路径片段（不区分大小写）：set/status 对含这些片段的键做拦截/脱敏
SENSITIVE_KEY_PARTS = ("api_key", "token", "secret")

# AI 额度厂商 key 所在顶层配置节（平铺 key 配置后 key 直接位于该节下）
SENSITIVE_SECTION = "ai_quota"

# 影响调度器的配置键：变更后需重启调度循环
SCHEDULER_KEYS = ("basic.enabled", "basic.push_time", "basic.timezone")


class AdminCommandError(Exception):
    """命令执行错误，message 为用户可读的提示。"""


def strip_prefix(text: str, prefix: str) -> str | None:
    """大小写不敏感剥离命令前缀；前缀之后须为空或空白，否则返回 None。"""
    lowered_text = text.strip()
    lowered_prefix = prefix.strip().lower()
    if not lowered_prefix:
        return None
    if not lowered_text.lower().startswith(lowered_prefix):
        return None
    rest = lowered_text[len(lowered_prefix) :]
    if rest and not rest[0].isspace():
        return None
    return rest.strip()


def parse_command(command: str) -> tuple[str, list[str]]:
    """拆分子命令与参数列表（按空白切分，子命令小写化）。"""
    parts = command.split()
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


def convert_value(raw: str) -> Any:
    """按规则转换值为目标类型：bool / int / float / List[str] / str。"""
    value = raw.strip()
    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if "," in value or "，" in value:
        return [part.strip() for part in value.replace("，", ",").split(",") if part.strip()]
    return value


def is_sensitive_key(key: str) -> bool:
    """键路径是否为敏感配置（AI 额度 key 或含 api_key/token/secret 的字段）。"""
    lowered = key.lower()
    if lowered == SENSITIVE_SECTION or lowered.startswith(f"{SENSITIVE_SECTION}."):
        return True
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def affects_scheduler(key: str) -> bool:
    """配置键变更后是否需要重启调度器。"""
    return key in SCHEDULER_KEYS


def set_nested(config_data: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    """在配置字典副本上按点分路径写入值，返回新字典（原字典不变）。"""
    result = deepcopy(config_data)
    parts = [part.strip() for part in key.split(".") if part.strip()]
    if not parts:
        raise AdminCommandError("配置键不能为空")
    current = result
    for part in parts[:-1]:
        next_value = current.get(part)
        if next_value is None:
            next_value = {}
            current[part] = next_value
        if not isinstance(next_value, dict):
            raise AdminCommandError(f"配置路径 {part} 已存在且不是配置节")
        current = next_value
    current[parts[-1]] = value
    return result


def get_nested(config_data: dict[str, Any], key: str) -> Any:
    """读取点分路径值；路径不存在或类型不符返回 None。"""
    current = config_data
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def flatten_config(config_data: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    """将嵌套配置展平为 (点分键, 值) 列表（值类型为 dict 的嵌套节继续展开）。"""
    items: list[tuple[str, Any]] = []
    for key, value in config_data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            items.extend(flatten_config(value, full_key))
        else:
            items.append((full_key, value))
    return items


def format_value(value: Any) -> str:
    """将配置值格式化为可读文本。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    if value is None:
        return "（未设置）"
    return str(value)


def build_status_text(config_data: dict[str, Any]) -> str:
    """构建配置摘要文本，敏感字段值以 **** 脱敏。"""
    lines = ["【早报当前配置】"]
    for key, value in flatten_config(config_data):
        shown = "****" if is_sensitive_key(key) else format_value(value)
        lines.append(f"{key} = {shown}")
    return "\n".join(lines)


def build_help_text(prefix: str) -> str:
    """构建命令帮助文本（含仅运行时生效提示）。"""
    return (
        f"【早报管理命令】前缀 {prefix}（大小写不敏感），仅管理员在目标群内可用：\n"
        f"{prefix} help —— 本帮助\n"
        f"{prefix} status —— 查看当前配置（敏感字段脱敏）\n"
        f"{prefix} set <键> <值> —— 修改配置，如 {prefix} set basic.push_time 09:00；"
        "true/false→布尔，数字→数值，逗号分隔→列表\n"
        f"{prefix} reset <键> —— 恢复该配置项默认值\n"
        f"{prefix} push —— 立即推送一次早报\n"
        "注意：命令修改仅运行时生效，重启后恢复 WebUI 配置值；"
        "AI 额度 key 与含 api_key/token/secret 的字段请到 WebUI 修改。"
    )
