from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from core.config import Settings
from core.message_service import MessageService
from core.plugin_manager import PluginManager
from core.storage import SQLiteStore
from core.time_utils import fmt_ts


def create_web_app(
    settings: Settings,
    store: SQLiteStore,
    message_service: MessageService,
    plugin_manager: PluginManager,
) -> FastAPI:
    app = FastAPI(title="weijian-core webui")
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

    def _plugin_menus() -> list[dict[str, str]]:
        return plugin_manager.list_frontend_menu_items()

    def _check_admin_token(x_admin_token: str | None) -> JSONResponse | None:
        if x_admin_token != settings.admin_token:
            print("[admin] unauthorized request")
            return JSONResponse(status_code=401, content={"ok": False, "message": "unauthorized"})
        return None

    @app.get("/ui", response_class=HTMLResponse)
    async def ui_dashboard(request: Request) -> Any:
        scheduler = message_service.scheduler_status()
        context = {
            "request": request,
            "active_nav": "/ui",
            "plugin_menus": _plugin_menus(),
            "service_status": "running",
            "ws_host": settings.napcat_ws_host,
            "ws_port": settings.napcat_ws_port,
            "scheduler_running": scheduler["running"],
            "scheduler_error": scheduler["last_error"],
            "plugin_count": len(plugin_manager.list_plugins()),
            "plugin_rule_count": message_service.plugin_rules_count(),
        }
        print("[webui] GET /ui")
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=context,
        )

    @app.get("/ui/notes", response_class=HTMLResponse)
    async def ui_notes(request: Request) -> Any:
        notes = store.list_notes(limit=100)
        note_items = [
            {
                "id": n.id,
                "user_id": n.user_id,
                "content": n.content,
                "created_at": fmt_ts(n.created_at),
            }
            for n in notes
        ]
        print("[webui] GET /ui/notes")
        return templates.TemplateResponse(
            request=request,
            name="notes.html",
            context={
                "request": request,
                "active_nav": "/ui/notes",
                "plugin_menus": _plugin_menus(),
                "notes": note_items,
            },
        )

    @app.get("/ui/reminders", response_class=HTMLResponse)
    async def ui_reminders(request: Request, status: str = "all") -> Any:
        normalized = status if status in {"pending", "done", "cancelled"} else "all"
        reminders = store.list_reminders(status=None if normalized == "all" else normalized, limit=100)
        reminder_items = [
            {
                "id": r.id,
                "user_id": r.user_id,
                "content": r.content,
                "status": r.status,
                "remind_at": fmt_ts(r.remind_at),
                "created_at": fmt_ts(r.created_at),
            }
            for r in reminders
        ]
        print(f"[webui] GET /ui/reminders?status={normalized}")
        return templates.TemplateResponse(
            request=request,
            name="reminders.html",
            context={
                "request": request,
                "active_nav": "/ui/reminders",
                "plugin_menus": _plugin_menus(),
                "status": normalized,
                "reminders": reminder_items,
            },
        )

    @app.get("/ui/plugins", response_class=HTMLResponse)
    async def ui_plugins(request: Request) -> Any:
        plugins = plugin_manager.list_plugins()
        print("[webui] GET /ui/plugins")
        return templates.TemplateResponse(
            request=request,
            name="plugins.html",
            context={
                "request": request,
                "active_nav": "/ui/plugins",
                "plugin_menus": _plugin_menus(),
                "plugins": plugins,
            },
        )

    @app.get("/ui/ext/{ext_path:path}", response_class=HTMLResponse)
    async def ui_plugin_page(ext_path: str, request: Request) -> Any:
        route = f"/ui/ext/{ext_path}".rstrip("/") or "/ui/ext"
        page = plugin_manager.resolve_frontend_page(route)
        if page is None:
            return HTMLResponse(status_code=404, content=f"插件页面不存在: {route}")

        view_type = str(page.get("view_type", "")).strip().lower()
        source = str(page.get("source", "")).strip()
        plugin_name = str(page.get("plugin", "")).strip()
        title = str(page.get("title", "插件页面"))

        print(f"[webui] GET {route} plugin={plugin_name}, view_type={view_type}, source={source}")

        if view_type == "iframe":
            return templates.TemplateResponse(
                request=request,
                name="plugin_iframe.html",
                context={
                    "request": request,
                    "active_nav": route,
                    "plugin_menus": _plugin_menus(),
                    "title": title,
                    "iframe_url": source,
                },
            )

        if view_type == "template":
            try:
                file_path = plugin_manager.plugin_file_path(plugin_name, source)
                if not file_path.exists() or not file_path.is_file():
                    return HTMLResponse(
                        status_code=404,
                        content=f"插件模板不存在: {plugin_name}/{source}",
                    )
                html = file_path.read_text(encoding="utf-8")
            except Exception as exc:
                return HTMLResponse(status_code=500, content=f"插件页面加载失败: {exc}")

            return templates.TemplateResponse(
                request=request,
                name="plugin_raw_page.html",
                context={
                    "request": request,
                    "active_nav": route,
                    "plugin_menus": _plugin_menus(),
                    "title": title,
                    "plugin": plugin_name,
                    "html": html,
                },
            )

        return HTMLResponse(status_code=400, content=f"不支持的view_type: {view_type}")

    @app.post("/admin/reload_plugins")
    async def admin_reload_plugins(x_admin_token: str | None = Header(default=None)) -> JSONResponse:
        unauthorized = _check_admin_token(x_admin_token)
        if unauthorized:
            return unauthorized
        result = plugin_manager.reload_all()
        print(f"[admin] POST /admin/reload_plugins => {result}")
        return JSONResponse(content={"ok": bool(result.get("ok")), "message": str(result.get("message", ""))})

    @app.post("/admin/reload_plugin/{name}")
    async def admin_reload_plugin(name: str, x_admin_token: str | None = Header(default=None)) -> JSONResponse:
        unauthorized = _check_admin_token(x_admin_token)
        if unauthorized:
            return unauthorized
        result = plugin_manager.reload_plugin(name)
        print(f"[admin] POST /admin/reload_plugin/{name} => {result}")
        return JSONResponse(content={"ok": bool(result.get("ok")), "message": str(result.get("message", ""))})

    @app.post("/admin/reminders/{reminder_id}/cancel")
    async def admin_cancel_reminder(
        reminder_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> JSONResponse:
        unauthorized = _check_admin_token(x_admin_token)
        if unauthorized:
            return unauthorized
        ok = store.cancel_reminder_by_id(reminder_id=reminder_id)
        msg = "cancelled" if ok else "reminder not found or not pending"
        print(
            f"[admin] POST /admin/reminders/{reminder_id}/cancel => ok={ok}, message={msg}"
        )
        return JSONResponse(content={"ok": ok, "message": msg})

    @app.post("/admin/reminders/cleanup_done")
    async def admin_cleanup_done(x_admin_token: str | None = Header(default=None)) -> JSONResponse:
        unauthorized = _check_admin_token(x_admin_token)
        if unauthorized:
            return unauthorized
        count = store.clear_done_reminders_global()
        msg = f"done reminders removed: {count}"
        print(f"[admin] POST /admin/reminders/cleanup_done => {msg}")
        return JSONResponse(content={"ok": True, "message": msg})

    return app
