from __future__ import annotations

import asyncio
from pathlib import Path

import uvicorn
from api.webui_app import create_web_app
from connectors.napcat.http_client import NapCatHttpClient
from connectors.napcat.ws_server import run_ws_server
from core.config import load_settings
from core.message_service import MessageService
from core.plugin_manager import PluginManager
from core.runtime_log import setup_runtime_logging
from core.storage import SQLiteStore


async def _main() -> None:
    setup_runtime_logging(Path("data/runtime.log"))
    settings = load_settings()

    napcat_http = NapCatHttpClient(
        base_url=settings.napcat_http_base,
        token=settings.napcat_http_token,
    )
    store = SQLiteStore(database_url=settings.database_url)
    message_service = MessageService(napcat_http=napcat_http, store=store)
    plugin_manager = PluginManager(plugins_dir=Path("plugins"), message_service=message_service)
    plugin_manager.reload_all()

    web_app = create_web_app(
        settings=settings,
        store=store,
        message_service=message_service,
        plugin_manager=plugin_manager,
    )
    web_config = uvicorn.Config(
        app=web_app,
        host=settings.webui_host,
        port=settings.webui_port,
        log_level="warning",
    )
    web_server = uvicorn.Server(web_config)

    print(f"APP_PORT={settings.app_port}")
    print(f"[webui] listening on http://{settings.webui_host}:{settings.webui_port}")
    await asyncio.gather(
        run_ws_server(
            host=settings.napcat_ws_host,
            port=settings.napcat_ws_port,
            message_service=message_service,
        ),
        message_service.run_reminder_scheduler(),
        web_server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(_main())