
import json

KEEP_PATHS = {
    "/send_private_msg",
    "/send_group_msg",
    "/get_login_info",
    "/get_status",
}

with open("docs/napcat/openapi-full.json", "r", encoding="utf-8") as f:
    spec = json.load(f)

mini = {
    "openapi": spec.get("openapi"),
    "info": spec.get("info"),
    "paths": {},
    "components": spec.get("components", {}),  # 先全留，省事
}

for p, v in spec.get("paths", {}).items():
    if p in KEEP_PATHS:
        mini["paths"][p] = v

with open("docs/napcat/openapi-min.json", "w", encoding="utf-8") as f:
    json.dump(mini, f, ensure_ascii=False, indent=2)

print("done:", list(mini["paths"].keys()))