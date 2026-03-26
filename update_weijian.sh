#!/usr/bin/env sh
set -eu

# ===== 可改参数 =====
APP_DIR="${APP_DIR:-/vol1/1000/docker/weijian}"   # 你的项目目录
BRANCH="${BRANCH:-main}"
REMOTE="${REMOTE:-origin}"
# ====================

echo "[1/7] 进入目录: $APP_DIR"
cd "$APP_DIR"

if [ ! -f "docker-compose.yml" ]; then
  echo "ERROR: 当前目录没有 docker-compose.yml"
  exit 1
fi

echo "[2/7] 备份关键文件"
TS="$(date +%Y%m%d_%H%M%S)"
mkdir -p "./backup/$TS"
[ -f ".env" ] && cp .env "./backup/$TS/.env.bak" || true
[ -d "plugins" ] && cp -r plugins "./backup/$TS/plugins.bak" || true
[ -f "docker-compose.yml" ] && cp docker-compose.yml "./backup/$TS/docker-compose.yml.bak" || true

echo "[3/7] 拉取最新代码"
if [ -d ".git" ]; then
  git fetch "$REMOTE"
  git checkout "$BRANCH"
  git pull --rebase "$REMOTE" "$BRANCH"
else
  echo "WARN: 当前不是 git 仓库，跳过 git 更新（请手工覆盖文件）"
fi

echo "[4/7] 校验 compose"
docker compose config >/dev/null

echo "[5/7] 更新镜像（可选）"
docker compose pull || true

echo "[6/7] 重建并启动"
docker compose up -d --build --remove-orphans

echo "[7/7] 完成，当前状态："
docker compose ps

echo "OK: 更新完成。建议打开 /ui/logs 检查运行日志。"