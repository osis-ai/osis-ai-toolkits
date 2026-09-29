# OSIS Plugin

给 Codex 与 Claude Code 用的 OSIS Agent 插件。**同一个 Skill 源、同一个 MCP endpoint**，两侧只差 manifest 与 MCP 配置格式。

## 组成

| 文件 | 宿主 | 作用 |
|---|---|---|
| `plugin.json` | Codex | 便携 manifest（`agent-plugins.org` schema） |
| `mcp.json` | Codex | MCP 配置，`type: streamable-http` |
| `.codex-plugin/plugin.json` | Codex | 兼容层 |
| `.claude-plugin/plugin.json` | Claude Code | manifest（`name` 必填、kebab-case） |
| `.mcp.json` | Claude Code | MCP 配置，`type: http` |
| `skills/` | 两者共用 | 唯一 Skill 源 |
| `tests/` | — | manifest 与 Skill 校验 |

两侧的 MCP 都指向同一个地址：

```json
http://127.0.0.1:18080/mcp
```

## Skill

- **`skills/osis/SKILL.md`** —— 核心入口。规定标准工作流、实例选择、错误码应对、铁律，以及 OpenCode 专属内容在本宿主的替代方式。
- `skills/osis/references/` —— `concepts.md` / `common-workflows.md` / `troubleshooting.md` / `examples.md`
- `skills/osis-engine/`、`skills/osis-bridge-*/`、`skills/osis-module-*/` 等 —— 领域知识，从 OpenCode 版本迁移而来。

### 与 OpenCode 版本的差异

这些是 OpenCode 专属的，在 Codex / Claude Code 中**不可用**（核心 Skill §4 已统一说明）：

| OpenCode | 本插件 |
|---|---|
| 内置 `question` 工具 | 普通文本反问 |
| WeKnora MCP（`list_knowledge_bases` / `hybrid_search` / …） | `get_api_help` MCP 工具，或直接读 skill 自带 `scripts/`、`references/templates/` |
| `%OSIS_EXTRA_CONFIG_DIR%` | `<插件>/skills/`（读到的 SKILL.md 所在目录） |
| `osis-memory` 工具 | 直接读写 `~/.osisai/memory/PROFILE.md` |
| 本地 `python xxx.py` | `execute_python` MCP 工具 |

## MCP 工具

```text
list_instances()                           列出可用实例
get_instance_info(instance_id)             操作前二次确认
get_api_help(query?, symbol?)              真实 OSIS Python API 文档
execute_python(instance_id, code, timeout) 核心:在实例里执行 Python
raw_http_request(...)                      高级兼容入口,非日常工作流
```

不把几百个 OSIS API 做成 Tool —— 复杂操作由 Agent 写 Python 走 `execute_python`。
`get_api_help` 的内容来自本机 `pyosis` 的真实 docstring，与已安装版本对应。

## 故障排查

- **MCP 连不上** → Broker 未启动。启动 `osis-broker/scripts/run_broker.bat`，不要去猜 OSIS 端口。
- **改了 `mcp.json` / `.mcp.json` 的端口** → 必须两边同步，且与 Broker 的 `--port` 一致。`tests/test_manifests.py` 会拦下不一致。
- 其余（实例离线、409、超时、Python 异常、API 查不到）见 `skills/osis/references/troubleshooting.md`。

## 测试

```bat
%USERPROFILE%\.osisai\.venv\Scripts\python.exe -m pytest plugins/osis/tests -q
```
