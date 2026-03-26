from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _find_napcat_config(root: Path) -> Path:
    candidates = sorted(root.glob("onebot11_*.json"))
    if candidates:
        return candidates[0]
    raise FileNotFoundError("未找到 onebot11_*.json，请用 --config 指定 NapCat 配置文件路径")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ensure_http_server(config: dict[str, Any], token: str) -> None:
    network = config.setdefault("network", {})
    http_servers = network.setdefault("httpServers", [])
    if not http_servers:
        http_servers.append(
            {
                "enable": True,
                "name": "weijian-http",
                "host": "0.0.0.0",
                "port": 3000,
                "enableCors": True,
                "enableWebsocket": True,
                "messagePostFormat": "array",
                "token": token,
                "debug": False,
            }
        )
        return

    server = http_servers[0]
    server["enable"] = True
    server.setdefault("name", "weijian-http")
    server.setdefault("host", "0.0.0.0")
    server.setdefault("port", 3000)
    server.setdefault("enableCors", True)
    server.setdefault("enableWebsocket", True)
    server.setdefault("messagePostFormat", "array")
    server["token"] = token


def _ensure_ws_client(config: dict[str, Any], ws_url: str, token: str) -> None:
    network = config.setdefault("network", {})
    ws_clients = network.setdefault("websocketClients", [])

    found = None
    for client in ws_clients:
        if client.get("name") == "weijian-ws":
            found = client
            break

    if found is None:
        found = {
            "enable": True,
            "name": "weijian-ws",
            "url": ws_url,
            "reportSelfMessage": False,
            "messagePostFormat": "array",
            "token": token,
            "debug": False,
            "heartInterval": 30000,
            "reconnectInterval": 30000,
        }
        ws_clients.append(found)
    else:
        found["enable"] = True
        found["url"] = ws_url
        found["token"] = token
        found.setdefault("reportSelfMessage", False)
        found.setdefault("messagePostFormat", "array")
        found.setdefault("debug", False)
        found.setdefault("heartInterval", 30000)
        found.setdefault("reconnectInterval", 30000)


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        out[k.strip()] = v
    return out


def _write_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    handled: set[str] = set()
    out: list[str] = []

    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in raw:
            out.append(raw)
            continue
        k, _ = raw.split("=", 1)
        key = k.strip()
        if key in updates:
            out.append(f"{key}={updates[key]}")
            handled.add(key)
        else:
            out.append(raw)

    miss = [k for k in updates if k not in handled]
    if miss:
        if out and out[-1].strip() != "":
            out.append("")
        out.append("# ===== Updated by tools/setup_napcat.py =====")
        for k in miss:
            out.append(f"{k}={updates[k]}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="自动配置 NapCat 与 weijian 对接")
    parser.add_argument("--mode", choices=["local", "docker"], default="local", help="部署模式")
    parser.add_argument("--root", default=".", help="项目根目录")
    parser.add_argument("--config", default="", help="NapCat onebot11 配置文件路径")
    parser.add_argument("--env", default=".env", help=".env 文件路径（相对 root）")
    parser.add_argument("--ws-url", default="", help="NapCat websocket client URL，留空按 mode 自动")
    parser.add_argument("--token", default="", help="NapCat HTTP/WS token，留空表示不鉴权")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    env_path = (root / args.env).resolve()
    env_values = _read_env(env_path)

    ws_port = int(env_values.get("NAPCAT_WS_PORT", "8095"))
    default_ws_url = f"ws://127.0.0.1:{ws_port}/" if args.mode == "local" else f"ws://weijian-core:{ws_port}/"
    ws_url = args.ws_url or default_ws_url

    http_base = "http://127.0.0.1:13001" if args.mode == "local" else "http://napcat:3000"
    token = args.token

    if args.config:
        config_path = Path(args.config).resolve()
    else:
        config_path = _find_napcat_config(root)

    data = _load_json(config_path)
    _ensure_http_server(data, token=token)
    _ensure_ws_client(data, ws_url=ws_url, token=token)
    _save_json(config_path, data)

    _write_env(
        env_path,
        {
            "NAPCAT_HTTP_BASE": http_base,
            "NAPCAT_HTTP_TOKEN": token,
        },
    )

    print("[ok] NapCat 配置已更新:", config_path)
    print("[ok] .env 已更新:", env_path)
    print(f"[info] mode={args.mode}, ws_url={ws_url}, http_base={http_base}, token={'on' if token else 'off'}")
    print("[next] 重启对应服务后生效")


if __name__ == "__main__":
    main()
