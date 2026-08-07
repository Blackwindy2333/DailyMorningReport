"""MiSans 字体内嵌：读取 assets/fonts 下的 woff2 子集字体，转 base64 data URL 注入 @font-face。

由于渲染 allow_network=False 且 HTML 字符串传入，字体必须内嵌为 base64 data URL。
字体为 GB2312 常用字子集（约 900KB/字重），覆盖中文常用字 + 拉丁 + 标点。
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

_ASSETS_FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# 字重 → 文件名
_WEIGHTS = {
    "400": "MiSans-Regular.woff2",
    "500": "MiSans-Medium.woff2",
    "700": "MiSans-Bold.woff2",
    "800": "MiSans-Heavy.woff2",
}


@lru_cache(maxsize=1)
def get_font_faces() -> str:
    """返回 MiSans 各字重的 @font-face CSS 块（含 base64 data URL）。"""
    faces = []
    for weight, filename in _WEIGHTS.items():
        path = _ASSETS_FONTS / filename
        if not path.exists():
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        faces.append(
            "@font-face{"
            f"font-family:'MiSans';"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');"
            f"font-weight:{weight};"
            "font-display:swap;"
            "}"
        )
    return "\n".join(faces)


@lru_cache(maxsize=1)
def get_font_stack() -> str:
    """返回 font-family 栈（MiSans 优先，回退系统字体）。"""
    return '"MiSans", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif'