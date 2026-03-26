from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_env(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        values[k.strip()] = v.strip()
    return values


def _build_config(ws_url: str, token: str, name: str, http_name: str, http_port: int) -> dict:
    return {
        "network": {
            "httpServers": [
                {
                    "enable": True,
                    "name": http_name,
                    "host": "0.0.0.0",
                    "port": http_port,
                    "enableCors": True,
                    "enableWebsocket": True,
                    "messagePostFormat": "array",
                    "token": token,
                    "debug": False,
                }
            ],
            "httpSseServers": [],
            "httpClients": [],
            "websocketServers": [],
            "websocketClients": [
                {
                    "enable": True,
                    "name": name,
                    "url": ws_url,
                    "reportSelfMessage": False,
                    "messagePostFormat": "array",
                    "token": token,
                    "debug": False,
                    "heartInterval": 30000,
                    "reconnectInterval": 30000,
                }
            ],
            "plugins": [],
        },
        "musicSignUrl": "",
        "enableLocalFile2Url": False,
        "parseMultMsg": False,
        "imageDownloadProxy": "",
        "timeout": {
            "baseTimeout": 10000,
            "uploadSpeedKBps": 256,
            "downloadSpeedKBps": 256,
            "maxTimeout": 1800000,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="根据 .env 生成 NapCat OneBot 配置")
    parser.add_argument("--env-file", default=".env", help=".env 文件路径")
    parser.add_argument("--out-dir", default="napcat_data/config", help="NapCat 配置目录")
    parser.add_argument("--ws-url", default="ws://weijian-core:8095/", help="NapCat 回连 WS 地址")
    parser.add_argument("--ws-name", default="weijian-ws", help="NapCat websocket client 名称")
    parser.add_argument("--http-name", default="weijian-http", help="NapCat http server 名称")
    parser.add_argument("--http-port", type=int, default=3000, help="NapCat http server 监听端口")
    parser.add_argument("--force", action="store_true", help="覆盖已存在配置")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    env_values = _read_env(env_path)

    bot_qq = env_values.get("BOT_QQ", "").strip()
    token = env_values.get("NAPCAT_HTTP_TOKEN", "")
    if not bot_qq:
        raise SystemExit("缺少 BOT_QQ，请先在 .env 配置")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"onebot11_{bot_qq}.json"

    if out_file.exists() and not args.force:
        print(f"配置已存在，跳过生成: {out_file}")
        return 0

    config = _build_config(
        ws_url=args.ws_url,
        token=token,
        name=args.ws_name,
        http_name=args.http_name,
        http_port=args.http_port,
    )

    out_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成 NapCat 配置: {out_file}")
    print(f"WS 回连: {args.ws_url}")
    print(f"HTTP 监听: 0.0.0.0:{args.http_port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
