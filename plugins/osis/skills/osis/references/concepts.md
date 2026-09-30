# 概念

## OSIS Agent Broker

本机唯一的服务，监听 `127.0.0.1:18080`（仅 loopback，不对外）。它把「一堆 OSIS 实例」收敛成一个稳定入口：

```text
Codex / Claude Code
        │  Plugin（Skill + MCP 配置）
        ▼
OSIS Agent Broker  127.0.0.1:18080
        ├─ InstanceRegistry   接收 heartbeat，维护在线实例
        ├─ HTTP ReverseProxy  /instances/{id}/{path} → 实例真实端口
        ├─ MCP Server         /mcp （Streamable HTTP）
        ├─ ApiHelp            pyosis API 索引检索
        └─ Health             /health
        ▼
本机的 OSIS 实例（各自监听不同端口）
```

Broker **可以**在 OSIS 全部未启动时正常启动 —— 那时 `list_instances` 返回空数组。

## 实例（instance）

一个打开的 OSIS 窗口/进程。Broker 从 heartbeat 维护：

| 字段 | 含义 |
|---|---|
| `instance_id` | 实例唯一 ID，重启后**改变** |
| `pid` | 进程号 |
| `port` | 该实例真实 HTTP 端口（**不要暴露给用户**） |
| `project` | 打开的模型路径，如 `D:/models/test.osis` |
| `version` | OSIS 软件版本 |
| `state` | `starting` / `ready` / `busy` / `closing` / `offline` |
| `window_title` | 窗口标题，通常就是模型名 |
| `last_seen` | 最近一次 heartbeat 时间 |

超过 TTL 未收到 heartbeat，实例被标记 `offline`，再过一段时间从可用列表移除。**不需要** OSIS 主动注销 —— 闪退、被任务管理器结束都能正确反映。

## 状态化模型

OSIS 是有状态的软件：模型数据驻留在 OSIS 进程内，不在 `.py` 文件里。因此：

- `execute_python` 里的 `engine` 每次都连到该实例当前的模型状态。
- 改磁盘上的 `py/prep/*.py` 不等于模型变了，必须执行写回（见 `common-workflows.md`）。
- 实例重启后模型状态从磁盘重新加载，`instance_id` 也换了。

## 实例路由与透传

`execute_python` 的执行模型（见 `SKILL.md §1.4`）：Broker 起 OSIS 官方 Python 子进程，
子进程的 pyosis 请求打到 **Broker 的显式实例路由**：

`ANY http://127.0.0.1:18080/instances/A81F/<path>` → 转发成

`ANY http://127.0.0.1:<A81F 真实端口>/<path>`

`raw_http_request` 也走同一代理。Broker 不重新实现 OSIS 的业务 API，只做
Method / Path / Query / Body / Content-Type / 状态码的透明转发。

**不再注入 `X-OSIS-Instance-ID`**（2026-09-30 变更）：OSIS 已不校验实例身份，
也不再由 OSIS 生成/回传 `instance_id`。身份保证由 **Broker 心跳层**承担：

- 实例 ID 由 Broker 按 `(port, pid)` 稳定分配与复用；
- 同端口换 pid（实例重启/端口被新进程占用）→ 旧 `instance_id` 立即 `offline`，
  后续 `execute_python`/代理在**发出任何请求前**就被 `registry` 拒绝；
- 请求前的存活/状态校验 + Skill 层操作前确认与修改后读回验证。

若上游仍返回 `409 INSTANCE_MISMATCH`（旧版 OSIS/中间层），Broker 会结构化返回
并复核实例状态（兼容保留；当前 OSIS 不会发送）。

## API 索引

`get_api_help` 的内容来自本机 `pyosis` 包（PyPI 名 `osis-python`）的真实 docstring —— 与已安装 OSIS 版本对应。索引在 Broker 首次启动时反射生成并缓存，**不**把几千个函数塞进 Skill。

## 与 OpenCode 版本的关系

原 OpenCode 侧的 skill（`osis-engine`、`osis-bridge-*`、`osis-module-*` 等）被原样搬进本插件，作为**领域知识**继续有效。变化的只有「怎么执行」：

| | OpenCode | Codex / Claude Code |
|---|---|---|
| 执行 Python | 本地 shell `python xxx.py` | `execute_python` MCP 工具 |
| 查 API | WeKnora MCP + `pyosis_doc.py` | `get_api_help` MCP 工具（也可直接读 skill 附带脚本） |
| 反问用户 | 内置 `question` 工具 | 普通文本提问 |
| 找工程目录 | `%OSIS_EXTRA_CONFIG_DIR%` | 从 `get_instance_info().project` 推导 |
