from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_port: int
    napcat_ws_host: str
    napcat_ws_port: int
    napcat_http_base: str
    napcat_http_token: str
    database_url: str
    webui_host: str
    webui_port: int
    admin_token: str


def load_settings() -> Settings:
    return Settings(
        app_port=int(os.getenv("APP_PORT", "8017")),
        napcat_ws_host=os.getenv("NAPCAT_WS_HOST", "0.0.0.0"),
        napcat_ws_port=int(os.getenv("NAPCAT_WS_PORT", "8095")),
        napcat_http_base=os.getenv("NAPCAT_HTTP_BASE", "http://127.0.0.1:3000").rstrip("/"),
        napcat_http_token=os.getenv("NAPCAT_HTTP_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/weijian.db"),
        webui_host=os.getenv("WEBUI_HOST", "127.0.0.1"),
        webui_port=int(os.getenv("WEBUI_PORT", "8018")),
        admin_token=os.getenv("ADMIN_TOKEN", "change_me"),
    )