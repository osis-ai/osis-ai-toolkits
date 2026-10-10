# OSIS Plugin

给 Codex、Claude Code 等 Agent 用的 OSIS 插件。**同一个 Skill 源、同一套 MCP server**，各宿主只差 manifest 与 MCP 配置格式。

## 组成

| 文件 | 宿主 | 作用 |
|---|---|---|
| `plugin.json` | Codex | 便携 manifest（`agent-plugins.org` schema） |
| `mcp.json` | Codex | MCP 配置 |
| `.claude-plugin/plugin.json` | Claude Code | manifest（`name` 必填、kebab-case） |
| `.mcp.json` | Claude Code（ZCode、WorkBuddy 同样读这套） | MCP 配置 |
| `.qoder-plugin/plugin.json` | Qoder | manifest，MCP 内联 |
| `.minimax-plugin/plugin.json` | MiniMax Code | manifest，skills 逐个列出 |
| `osis.mcp.json` | MiniMax Code | MCP 配置 |
| `../../kimi.plugin.json` | Kimi Code | manifest（在仓库根，从仓库根安装），MCP 内联 |
| `skills/` | 全部共用 | 领域 skill 唯一源 |
| `tests/` | — | manifest 与 Skill 校验 |

各宿主配置同两个 MCP server：

| server | 类型 | 说明 |
|---|---|---|
| `osis` | stdio `cmd /c %USERPROFILE%\.osisai\.venv\Scripts\python.exe -P -m osis_broker --stdio` | OSIS Agent Broker。本机 `127.0.0.1:18080` 没有 Broker 就后台拉起一个(独立进程,OSIS 与其他会话共用,会话结束不退出),再把 MCP 消息转发给它;不用手动启动 Broker |
| `weknora` | stdio `cmd /c %USERPROFILE%\.osisai\.venv\Scripts\python.exe -P -m weknora_mcp_server`(用 OSIS 环境的 Python;`-P` 不把 cwd(宿主的项目目录)加进 sys.path,防止项目里的同名 .py 盖掉依赖;`cmd /c` 负责展开 `%USERPROFILE%`,Codex 不展开 command 里的变量) | 桥梁模板/知识库检索。key 不进配置:从环境变量 `WEKNORA_API_KEY` 读,没有也照常启动,只是知识库工具鉴权失败 |

## Skill

- 全部是领域 skill（`osis-engine`、`osis-bridge-*`、`osis-module-*` 等），**本目录就是唯一源，直接在这里改**。
- `osis-skill-enhance`（训练 / 评测工作台）的 `.agents/skills` 是指向本目录的本地联接，那边读写的也是这一份。
- 宿主中立写法规范见 `osis-skill-enhance/SKILL编写规则.md §11`。

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
各工具的参数说明在工具描述里；插件不再单独带 `osis` skill。需要 osis-broker ≥ 1.0.12(`--stdio`)。

不把几百个 OSIS API 做成 Tool —— 复杂操作由 Agent 写 Python 走 `execute_python`。
`api_*` 的内容来自 OSIS 执行环境里 `pyosis` 的真实签名与 docstring，与已安装版本对应。

## 故障排查

- **MCP 连不上** → 看 `~/.osisai/logs/stdio.log` 与 `broker.log`;常见原因是还没打开过 OSIS(`~/.osisai/.venv` 未装好),或里面的 osis-broker 低于 1.0.12。不要去猜 OSIS 端口。
- **`list_instances` 为空** → OSIS 没打开,或 OSIS 还没向 Broker 发心跳。
- **改 MCP 配置** → 所有宿主的配置（见上表）必须同步。`tests/test_manifests.py` 会拦下不一致。

## 测试

```bat
%USERPROFILE%\.osisai\.venv\Scripts\python.exe -m pytest plugins/osis/tests -q
```
