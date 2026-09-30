# 故障排查

## Broker 连不上

表现：MCP 工具调用失败 / `/mcp` 无法连接。

```
OSIS Agent Broker 当前不可连接。
请确认 OSIS Agent 服务已启动。
```

- 不要提示用户去猜 OSIS 实例端口。
- 开发阶段 Broker 需手动启动：`osis-broker/scripts/run_broker.bat`（会自动准备 `~/.osisai/.venv`）。
- Debug 日志：`osis-broker/scripts/run_broker.bat --debug`，输出监听地址、注册/过期、heartbeat、代理目标、MCP 连接与 tool 调用、HTTP status、异常、耗时。
- **日志默认不写用户 Python 脚本正文**；需要时用更高等级显式开启。

## `list_instances` 返回空

| 情况 | 说明 |
|---|---|
| OSIS 根本没开 | 正常，让用户打开一个 OSIS 实例 |
| OSIS 开了但列表为空 | OSIS 未发 heartbeat 或已超时；查 Broker debug 日志的 heartbeat 记录 |
| 列表里有但 `state=offline` | 心跳中断，OSIS 可能闪退 |

## `INSTANCE_NOT_FOUND` / `INSTANCE_OFFLINE`

- 实例重启过，ID 变了 → 重新 `list_instances`。
- 不要把旧 ID 映射到新实例。

## `INSTANCE_MISMATCH` (409)

**兼容性错误**：当前 OSIS 不再校验实例身份、不会发送 409（2026-09-30 变更），
看到它意味着上游是旧版 OSIS 或中间层返回的：

1. 重新 `list_instances` 拿最新映射。
2. 用新 `instance_id` 重试。
3. 仍失败 → 让用户升级 OSIS 或重启实例。

端口复用/实例重启的**正常防线是心跳层**：这类场景通常先表现为
`INSTANCE_OFFLINE` 或 ID 变化 —— 按上面的错误处理即可。

## `INSTANCE_NOT_READY`

`state` 是 `starting` 或 `closing`：

- `starting` → 等一下重试（模型还在加载）。
- `closing` → 实例正在关闭，不要继续写操作，问用户。

## `EXECUTION_TIMEOUT`

- 脚本确实耗时长（如全桥重建、求解）→ 加大 `timeout` 重试。
- 脚本卡死（死循环、等输入）→ 拆小任务。
- **超时只停止了本地子进程，不代表 OSIS 端已受理的操作被撤销**，也不代表之前的修改
  没生效；子进程启动的其他进程未必已终止。
- **重试前先读回**：`get_instance_info` 确认实例状态，再查询模型数据看操作是否已部分
  完成 —— **不要**直接重跑创建/修改命令（可能重复创建或清空重建）。

## `PYTHON_ERROR`

读 `exception.traceback`：

| 现象 | 处理 |
|---|---|
| `AttributeError` / `NameError`（API 名错） | `get_api_help` 查正确名字 |
| `TypeError` / `missing positional argument` | `get_api_help(symbol=...)` 看签名 |
| `XxxError: 组不存在` | 组名逐字一致问题，见 `osis-engine` 的组名约束 |
| `clear()` 后模型空了 | 误跑 `main.py`；查询任务不要跑写回 |

## `API_HELP_NOT_FOUND`

- 换更通用的中文关键词，或改用 `symbol` 精确查。
- 索引基于本机 `pyosis`；若版本与 OSIS 不符，说明 `~/.osisai/.venv` 里的 `osis-python` 需要更新（跑 `runtime-bootstrap`）。
- **不要**据此断言 OSIS 不支持该功能。

## `OSIS_HTTP_ERROR`

OSIS 侧返回非 2xx。看响应体：多为参数不合法或当前状态不允许该操作。若响应是 `INSTANCE_MISMATCH`，按上面 409 处理。

## 输出为空 / 结果不符预期

- OSIS 是状态化的，`execute_python` 看到的是**该实例当前**的模型。
- 修改是否写回了？改 `.py` 不等于改模型 —— 检查是否执行了写回。
- 是否连错了实例？`get_instance_info` 复核 `project`。

## Skill 里提到的工具不存在

原 skill 写给 OpenCode。以下在 Codex / Claude Code 中**没有**，按 `SKILL.md §4` 的替代方式处理：

- `question` → 普通文本提问
- WeKnora MCP（`list_knowledge_bases` / `hybrid_search` / `bridge_search_templates` / `download_bridge_template`）→ `get_api_help`，或读 skill 自带的 `scripts/`、`references/templates/`
- `osis-memory` → 直接读写 `~/.osisai/memory/PROFILE.md`
- `%OSIS_EXTRA_CONFIG_DIR%` → 本插件安装目录下的 `skills/`
- 本地 `python xxx.py` → `execute_python`
