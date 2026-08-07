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
            self.logger.exception("解析聊天流异常（group=%s user=%s）", group_id, user_id)
            return None
        if stream is None:
            self.logger.warning("聊天流解析为空（group=%s user=%s）", group_id, user_id)
            return None
        # 兼容对象与 dict 两种返回结构
        session_id = (
            stream.get("session_id")
            if isinstance(stream, dict)
            else getattr(stream, "session_id", None)
        )
        sid = str(session_id) if session_id else None
        self.logger.info(
            "聊天流解析: group=%s user=%s stream_type=%s session_id=%s",
            group_id, user_id, type(stream).__name__, sid,
        )
        return sid

    async def push_group_images(self, images: list[str], group_id: str) -> tuple[int, int]:
        """向指定群按序推送多张图，返回 (成功数, 总数)。"""
        stream_id = await self._resolve_stream(group_id=group_id)
        if not stream_id:
            self.logger.warning("未找到群 %s 的聊天流，跳过推送（共 %d 张图）", group_id, len(images))
            return 0, len(images)
        ok = 0
        for idx, image_base64 in enumerate(images):
            try:
                sent = await self.ctx.send.image(image_base64, stream_id)
                if sent:
                    ok += 1
                    self.logger.info("群 %s 第 %d/%d 张图发送成功", group_id, idx + 1, len(images))
                else:
                    self.logger.warning("群 %s 第 %d/%d 张图发送失败（返回 False）", group_id, idx + 1, len(images))
            except Exception as e:
                self.logger.exception("群 %s 第 %d/%d 张图发送异常: %s", group_id, idx + 1, len(images), e)
        return ok, len(images)

    async def push_private_image(self, image_base64: str, user_id: str) -> bool:
        """向管理员私聊推送一张图。"""
        stream_id = await self._resolve_stream(user_id=user_id)
        if not stream_id:
            self.logger.warning("未找到用户 %s 的聊天流，跳过私聊推送", user_id)
            return False
        try:
            sent = bool(await self.ctx.send.image(image_base64, stream_id))
            if not sent:
                self.logger.warning("用户 %s 私聊图片发送失败（返回 False）", user_id)
            return sent
        except Exception as e:
            self.logger.exception("用户 %s 私聊图片发送异常: %s", user_id, e)
            return False
