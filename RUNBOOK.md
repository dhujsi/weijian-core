# RUNBOOK

## 1) 本地启动步骤（main.py）

1. 安装依赖：
   - `pip install -r requirements.txt`
2. 配置环境：
   - 复制 `.env.example` 为 `.env`
   - 至少检查：`NAPCAT_HTTP_BASE`、`NAPCAT_HTTP_TOKEN`、`WEBUI_PORT`、`ADMIN_TOKEN`
3. 启动：
   - `python src/main.py`
4. 访问：
   - WebUI: `http://127.0.0.1:8018/ui`

## 2) NapCat 联调检查

### 2.1 WS 连接
- 需保证 NapCat reverse ws 指向本服务的 `NAPCAT_WS_HOST:NAPCAT_WS_PORT`
- 服务日志应出现：`NapCat reverse WS listening on ...`
- 收到私聊时应出现：`[ws] private text received ...`

### 2.2 HTTP 发送
- `NAPCAT_HTTP_BASE` 必须指向 NapCat HTTP API（宿主机端口映射）
- 发送时看日志：`[http] send_private_msg request ...`
- 成功：`[http] send_private_msg ok ...`

### 2.3 Token
- 若 NapCat 开启鉴权，`NAPCAT_HTTP_TOKEN` 必须正确
- 错误时通常返回 401/403，查看 HTTP 失败日志正文

## 3) 时区检查（Asia/Shanghai）

- 当前展示统一使用 `Asia/Shanghai`
- 通过以下页面确认时间显示：
   - `/ui/ext/notes`
   - `/ui/ext/reminders`
- 通过消息确认：提醒设置回执时间应符合中国时区直觉

## 4) 常见故障排查

### 4.1 端口占用
- 现象：启动失败，提示 address already in use
- 处理：
  - 修改 `.env` 中 `NAPCAT_WS_PORT` / `WEBUI_PORT`
  - 或释放占用进程后重启

### 4.2 消息收到了但没回
- 先看 `[ws] private text received`
- 再看 `[msg] reply` 是否出现
- 再看 `[http] send_private_msg ...` 是否报错
- 常见原因：NapCat HTTP 未开、token 错、登录态失效

### 4.3 提醒不触发
- 看 scheduler 是否运行：`[scheduler] reminder scheduler started`
- 看提醒是否入库为 `pending`
- 看触发日志：`[scheduler] trigger reminder ...`
- 时区与时间格式确认：`Asia/Shanghai` 显示是否符合预期
