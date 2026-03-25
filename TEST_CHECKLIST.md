# TEST CHECKLIST

## 1) 私聊回显
- 输入示例：`你好`
- 预期结果：机器人回 `你好`
- 失败看日志：`[ws]`、`[msg] reply`、`[http] send_private_msg`

## 2) 记一下
- 输入示例：`记一下 明天买牛奶`
- 预期结果：回复 `记下了`，并在 `/ui/notes` 可见新记录
- 失败看日志：`[msg] on_private_text`、`[db] note inserted`

## 3) 我最近记了什么
- 输入示例：`我最近记了什么`
- 预期结果：返回最近笔记列表（带时间）
- 失败看日志：`[db] recent notes fetched`、`[msg] reply`

## 4) 相对时间提醒触发
- 输入示例：`1分钟后提醒我 喝水`
- 预期结果：先回复“已设置提醒...”，随后收到 `[提醒#id] 喝水`
- 失败看日志：`[rule] reminder matched`、`[db] reminder inserted`、`[scheduler] trigger reminder`

## 5) 取消提醒
- 输入示例：`取消提醒 12`
- 预期结果：存在且 pending 时回复“已取消提醒”；否则“提醒不存在或不可取消”
- 失败看日志：`[rule] cancel reminder matched`、`[db] reminder cancel`

## 6) reload 单插件/全插件
- 输入示例：
  - 单插件：`POST /admin/reload_plugin/demo_echo`
  - 全插件：`POST /admin/reload_plugins`
- 预期结果：返回 JSON `{"ok": true, "message": "..."}`，插件改动即时生效
- 失败看日志：`[admin]`、`[plugin] load failed/reload failed`、`[plugin] rule matched`
