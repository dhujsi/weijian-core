from __future__ import annotations

import argparse
import os

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="重载 weijian 插件（调用 WebUI admin 接口）")
    parser.add_argument("name", nargs="?", default="all", help="插件名；默认 all 表示重载全部")
    parser.add_argument(
        "--base",
        default=os.getenv("WEIJIAN_ADMIN_BASE", "http://127.0.0.1:8018"),
        help="管理接口基础地址，默认 http://127.0.0.1:8018",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("ADMIN_TOKEN", "change_me"),
        help="X-Admin-Token，默认读取环境变量 ADMIN_TOKEN",
    )
    args = parser.parse_args()

    name = args.name.strip()
    base = args.base.rstrip("/")
    token = args.token

    if name == "all":
        url = f"{base}/admin/reload_plugins"
    else:
        url = f"{base}/admin/reload_plugin/{name}"

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers={"X-Admin-Token": token})
        try:
            data = resp.json()
        except Exception:
            print(f"[error] 非JSON响应: status={resp.status_code}, body={resp.text}")
            raise SystemExit(1)

    ok = bool(data.get("ok"))
    print(data)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
