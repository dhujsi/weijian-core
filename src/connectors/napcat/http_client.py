from __future__ import annotations

from typing import Any

import httpx


class NapCatHttpClient:
    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def send_private_msg(
        self,
        user_id: int,
        message: str,
        group_id: int | None = None,
    ) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "message": message,
        }
        print(
            f"[http] send_private_msg request: base={self._base_url}, "
            f"user_id={user_id}, message={message}, auth={'on' if self._token else 'off'}"
        )
        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            try:
                response = await client.post(
                    "/send_private_msg",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                print(f"[http] send_private_msg ok: status={response.status_code}, body={response.text}")
                return response.json()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text
                print(
                    f"send_private_msg failed: status={exc.response.status_code}, "
                    f"url={exc.request.url}, body={body}"
                )
                if exc.response.status_code == 502:
                    fallback_payload = {
                        "message_type": "private",
                        "user_id": user_id,
                        "message": message,
                    }
                    if group_id is not None:
                        fallback_payload["group_id"] = group_id
                    try:
                        fallback = await client.post(
                            "/send_msg",
                            json=fallback_payload,
                            headers=self._headers(),
                        )
                        fallback.raise_for_status()
                        print(
                            f"[http] send_msg fallback ok: status={fallback.status_code}, "
                            f"body={fallback.text}"
                        )
                        return fallback.json()
                    except Exception as fallback_exc:
                        print(f"[http] send_msg fallback failed: {fallback_exc}")
                return {
                    "status": "failed",
                    "retcode": exc.response.status_code,
                    "message": body,
                }
            except httpx.RequestError as exc:
                print(f"send_private_msg request error: {exc}")
                return {
                    "status": "failed",
                    "retcode": -1,
                    "message": str(exc),
                }