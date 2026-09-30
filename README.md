# OSIS AI Toolkits

一个 Git 仓库同时服务 **Codex** 和 **Claude Code**：共享同一份 Skill、同一个 MCP endpoint、同一套 README 与测试，只针对不同宿主维护很薄的 manifest 适配。

安装后，你可以直接在 Codex / Claude Code 里说：

> 检查当前模型并帮我修改材料参数，然后运行计算。

Agent 会自动：`list_instances` → （必要时）`get_api_help` → `execute_python` → 验证结果 → 报告。
**你不需要知道任何 OSIS 实例的真实端口。**

```text
Codex / Claude Code
        │  Plugin(Skill + MCP 配置)
        ▼
OSIS Agent Broker  127.0.0.1:18080        ← 另一个仓库:osis-broker
        ├─ InstanceRegistry / ReverseProxy / McpServer / ApiHelp / WebUI
        ▼
本机上的 OSIS 实例(各自监听不同端口)
```

## 仓库结构

```text
osis-ai-toolkits/
├── .agents/plugins/marketplace.json      Codex marketplace
├── .claude-plugin/marketplace.json       Claude Code marketplace
└── plugins/osis/
    ├── plugin.json            Codex 便携 manifest
    ├── mcp.json               Codex MCP 配置
    ├── .codex-plugin/plugin.json   Codex 兼容层
    ├── .claude-plugin/plugin.json  Claude Code manifest
    ├── .mcp.json              Claude Code MCP 配置
    ├── skills/                ← 唯一 Skill 源,Codex / Claude 共用
    │   ├── osis/SKILL.md      核心入口(按开发要求 §12)
    │   ├── osis-engine/       建模总控
    │   ├── osis-bridge-*/     六种桥型方案
    │   ├── osis-module-*/     模块层 API 与约束
    │   └── ...
    ├── README.md
    └── tests/                 manifest 与 Skill 校验
```

> Broker（Python MCP 服务）在另一个仓库：**`osis-broker`**。
> 本仓库只做 **MCP 配置、Skill、插件**。

## 安装

### Claude Code

```text
/plugin marketplace add hahahehe-coder/osis-ai-toolkits
/plugin install osis@osis-ai-toolkits
```

新开一个会话即可使用。

### Codex

```text
codex plugin marketplace add hahahehe-coder/osis-ai-toolkits
```

然后在 Codex 的 `/plugins` 中安装 **OSIS**。

> marketplace 名称（`osis-ai-toolkits`）与 plugin slug（`osis`）发布后保持稳定，不要改。

## 使用前提

插件只连本机 Broker：

```text
http://127.0.0.1:18080/mcp
```

**Broker 未启动时**，Agent 会收到连接失败并提示：

```text
OSIS Agent Broker 当前不可连接。
请确认 OSIS Agent 服务已启动。
```

开发阶段手动启动（会自动准备 `~/.osisai/.venv`）：

```bat
osis-broker\scripts\run_broker.bat --debug
```

在别人机器上实时安装 Broker（**用 uv,不用系统 pip**）：

```bat
uv pip install osis_broker-1.0.0-py3-none-any.whl     :: 由 osis-broker 仓库 uv build 产出
osis-broker --debug
:: 目标机器没有 pyosis 时:  uv pip install "osis-broker[pyosis]"
```

正式发布阶段 Broker 随 OSIS 产品一起分发。

**默认实例与失效规则**（手写脚本直接打 18080 时适用，详见 `osis-broker/docs/contract.md §2.4`）：

- 首个就绪实例自动成为默认目标；WebUI 顶部显示并可显式切换；
- 默认实例离线/关闭/移除 → **报错，绝不自动改用另一个模型**；
- 显式 `/instances/{id}/` 路由（`execute_python` 的 instance_id）不受切换影响；
- 不跨 Broker 重启持久化，重启后由首个就绪心跳重新绑定。

**CORS 实际策略**（与 `osis-broker/README.md` 一致）：精确白名单 + `127.0.0.1`/
`localhost` 任意端口 + `osisbim.com` 子域；非白名单来源服务端 403；设置
`OSIS_BROKER_TOKEN` 后跨源浏览器请求需 Bearer，同源 WebUI 与无 Origin 原生调用豁免。

## 测试

```bat
%USERPROFILE%\.osisai\.venv\Scripts\python.exe -m pytest plugins/osis/tests -q
```

覆盖：两侧 marketplace 结构、manifest 字段、MCP endpoint 一致性、端口全仓一致性、
核心 Skill 的必备规则与引用文件、Skill 完整性；若本机 Broker 正在运行，额外验证 MCP 可连。

## 相关仓库

| 仓库 | 职责 |
|---|---|
| `osis-ai-toolkits`（本仓库） | MCP 配置、Skill、Codex / Claude 插件 |
| `osis-broker` | Python Broker：实例注册、HTTP 透明代理、MCP Server、API 文档检索、WebUI |
| `osis-python-runtime` | `runtime-bootstrap`：准备 `~/.osisai/.venv` |

通信契约（OSIS ↔ Broker）见 `osis-broker/docs/contract.md`。
