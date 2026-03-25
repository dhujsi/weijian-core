from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets

from core.message_service import MessageService


def _extract_text(event: dict[str, Any]) -> str:
    raw_message = event.get("raw_message")
    if isinstance(raw_message, str) and raw_message:
        return raw_message

    message = event.get("message")
    if not isinstance(message, list):
        return ""

    text_parts: list[str] = []
    for segment in message:
        if not isinstance(segment, dict):
            continue
        if segment.get("type") != "text":
            continue
        data = segment.get("data")
        if not isinstance(data, dict):
            continue
        text = data.get("text")
        if isinstance(text, str):
            text_parts.append(text)
    return "".join(text_parts)


async def _handle_event(event: dict[str, Any], message_service: MessageService) -> None:
    post_type = event.get("post_type")
    if post_type == "meta_event":
        meta_event_type = event.get("meta_event_type")
        print(f"[ws] meta_event ignored: {meta_event_type}")
        return

    if post_type != "message":
        return

    if event.get("message_type") != "private":
        return

    user_id = event.get("user_id")
    if user_id is None:
        return

    group_id = event.get("group_id")

    text = _extract_text(event)
    if not text:
        print("[ws] private message without text ignored")
        return

    print(f"[ws] private text received: user_id={user_id}, text={text}")
    await message_service.on_private_text(user_id=user_id, text=text, group_id=group_id)


async def run_ws_server(host: str, port: int, message_service: MessageService) -> None:
    async def handler(ws: websockets.WebSocketServerProtocol) -> None:
        async for raw in ws:
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if isinstance(event, dict):
                try:
                    await _handle_event(event, message_service)
                except Exception as exc:
                    print(f"event handle failed: {exc}")
                    continue

    async with websockets.serve(handler, host, port):
        print(f"NapCat reverse WS listening on {host}:{port}")
        await asyncio.Future()