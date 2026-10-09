# OSIS Plugin

给 Codex 与 Claude Code 用的 OSIS Agent 插件。**同一个 Skill 源、同一个 MCP endpoint**，两侧只差 manifest 与 MCP 配置格式。

## 组成

| 文件 | 宿主 | 作用 |
|---|---|---|
| `plugin.json` | Codex | 便携 manifest（`agent-plugins.org` schema） |
| `mcp.json` | Codex | MCP 配置，`type: streamable-http` |
| `.claude-plugin/plugin.json` | Claude Code | manifest（`name` 必填、kebab-case） |
| `.mcp.json` | Claude Code | MCP 配置，`type: http` |
| `skills/` | 两者共用 | 唯一 Skill 源 |
| `tests/` | — | manifest 与 Skill 校验 |

两侧配置同两个 MCP server：

| server | 类型 | 说明 |
|---|---|---|
| `osis` | HTTP `http://127.0.0.1:18080/mcp` | OSIS Agent Broker |
| `weknora` | stdio `cmd /c %USERPROFILE%\.osisai\.venv\Scripts\python.exe <插件根>/scripts/weknora_launch.py`(用 OSIS 环境的 Python;`cmd /c` 负责展开 `%USERPROFILE%`,Codex 不展开 command 里的变量;插件根 Codex 写 `${PLUGIN_ROOT}`、Claude 写 `${CLAUDE_PLUGIN_ROOT}`) | 桥梁模板/知识库检索。key 不进配置:launcher 先读环境变量 `WEKNORA_API_KEY`,没有再读 Windows 用户变量(`setx` 写的,Codex 不把用户环境变量传给 MCP 子进程);都没有也照常启动 |

## Skill

- 全部是领域 skill（`osis-engine`、`osis-bridge-*`、`osis-module-*` 等），**从 `osis-skill-enhance/.agents/skills` 原样同步，不要在本仓库手改**：

```bat
python scripts\sync_skills.py          :: 默认源 ..\osis-skill-enhance\.agents\skills
```

同步结果与源 commit 记在 `skills/.synced-from`；`tests/test_manifests.py` 会拦下与源不一致的手改。
领域 skill 的宿主中立写法规范见源仓库 `SKILL编写规则.md §11`。

## MCP 工具

```text
list_instances()                           列出可用实例
get_instance_info(instance_id)             操作前二次确认
api_glob(pattern)                          通配符列 API(限定名 / engine.x.y 路径)
api_grep(pattern)                          正则搜签名与 docstring
api_read(symbol)                           单个 API 全文;歧义列候选
execute_python(instance_id, code, timeout) 核心:在实例里执行 Python
execute_apdl(instance_id, script|file)     执行 APDL 命令流(片段或 .sml/.out)
raw_http_request(...)                      高级兼容入口,非日常工作流
```

怎么用这些工具（选实例、查 API、写回、失败处理等规矩）由 Broker 在 MCP server instructions 里下发，
各工具的参数说明在工具描述里；插件不再单独带 `osis` skill。需要 osis-broker ≥ 1.0.10。

不把几百个 OSIS API 做成 Tool —— 复杂操作由 Agent 写 Python 走 `execute_python`。
`api_*` 的内容来自 OSIS 执行环境里 `pyosis` 的真实签名与 docstring，与已安装版本对应。

## 故障排查

- **MCP 连不上** → Broker 未启动。启动 `osis-broker/scripts/run_broker.bat`，不要去猜 OSIS 端口。
- **改了 `mcp.json` / `.mcp.json` 的端口** → 必须两边同步，且与 Broker 的 `--port` 一致。`tests/test_manifests.py` 会拦下不一致。

## 测试

```bat
%USERPROFILE%\.osisai\.venv\Scripts\python.exe -m pytest plugins/osis/tests -q
```
