"""推送器：群图片推送 + 管理员私聊推送。

使用 ctx.chat 解析真实聊天流（遵守会话 ID 规范，不自行计算 session_id）。
"""

from __future__ import annotations

import logging
from typing import Any


class Pusher:
    """封装群推送与私聊推送。"""

    def __init__(self, ctx: Any, logger: logging.Logger) -> None:
        self.ctx = ctx
        self.logger = logger

    async def _resolve_stream(self, group_id: str = "", user_id: str = "") -> str | None:
        """解析真实聊天流 session_id；解析不到返回 None。"""
        try:
            if group_id:
                stream = await self.ctx.chat.get_stream_by_group_id(group_id, platform="qq")
            elif user_id:
                stream = await self.ctx.chat.get_stream_by_user_id(user_id, platform="qq")
            else:
                return None
        except Exception:
            self.logger.exception("解析聊天流异常")
            return None
        if stream is None:
            return None
        session_id = getattr(stream, "session_id", None)
        return str(session_id) if session_id else None

    async def push_group_images(
        self, images: list[str], group_id: str
    ) -> tuple[int, int]:
        """向指定群按序推送多张图，返回 (成功数, 总数)。"""
        stream_id = await self._resolve_stream(group_id=group_id)
        if not stream_id:
            self.logger.warning("未找到群 %s 的聊天流，跳过推送", group_id)
            return 0, len(images)
        ok = 0
        for image_base64 in images:
            try:
                sent = await self.ctx.send.image(image_base64, stream_id)
                if sent:
                    ok += 1
                else:
                    self.logger.warning("群 %s 图片发送失败（返回 False）", group_id)
            except Exception:
                self.logger.exception("群 %s 图片发送异常", group_id)
        return ok, len(images)

    async def push_private_image(self, image_base64: str, user_id: str) -> bool:
        """向管理员私聊推送一张图。"""
        stream_id = await self._resolve_stream(user_id=user_id)
        if not stream_id:
            self.logger.warning("未找到用户 %s 的聊天流，跳过私聊推送", user_id)
            return False
        try:
            return bool(await self.ctx.send.image(image_base64, stream_id))
        except Exception:
            self.logger.exception("私聊图片发送异常")
            return False
