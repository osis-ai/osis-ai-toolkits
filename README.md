# OSIS AI Toolkits

一个 Git 仓库同时服务 **Codex** 和 **Claude Code**：共享同一份 Skill、同一个 MCP endpoint、同一套 README 与测试，只针对不同宿主维护很薄的 manifest 适配。

安装后，你可以直接在 Codex / Claude Code 里说：

> 检查当前模型并帮我修改材料参数，然后运行计算。

Agent 会自动：`list_instances` → （必要时）`api_glob`/`api_grep`/`api_read` → `execute_python` → 验证结果 → 报告。
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
    ├── mcp.json               Codex MCP 配置(osis Broker + weknora)
    ├── .claude-plugin/plugin.json  Claude Code manifest
    ├── .mcp.json              Claude Code MCP 配置(同上,格式不同)
    ├── skills/                Codex / Claude 共用
    │   ├── osis/SKILL.md      插件自有:Broker 用法入口
    │   ├── osis-engine/       ┐
    │   ├── osis-bridge-*/     │ 领域 skill:从 osis-skill-enhance
    │   ├── osis-module-*/     │ 原样同步(scripts/sync_skills.py),
    │   └── ...                ┘ 不要在本仓库手改
    ├── README.md
    └── tests/                 manifest、同步一致性校验
scripts/sync_skills.py         同步领域 skill
```

> Broker（Python MCP 服务）在另一个仓库：**`osis-broker`**。
> 本仓库只做 **MCP 配置、Skill、插件**。

## 安装

### Claude Code

```text
/plugin marketplace add osis-ai/osis-ai-toolkits
/plugin install osis@osis-ai-toolkits
```

新开一个会话即可使用。

### Codex

```text
codex plugin marketplace add osis-ai/osis-ai-toolkits
```

然后在 Codex 的 `/plugins` 中安装 **OSIS**，或命令行 `codex plugin add osis@osis-ai-toolkits`。

### 离线安装（无法访问 GitHub 的电脑）

两家都**不能直接装 zip**，必须先解压，再把解压目录当本地 marketplace：

1. 拷入 `osis-ai-toolkits-<版本>.zip`（发布方式见 [发布新版本](#发布新版本)），解压到**固定位置**，如 `D:\osis-ai-toolkits`（之后更新要覆盖到同一目录，别删）。
2. 安装：

   ```text
   :: Claude Code
   claude plugin marketplace add D:\osis-ai-toolkits
   claude plugin install osis@osis-ai-toolkits

   :: Codex
   codex plugin marketplace add D:\osis-ai-toolkits
   codex plugin add osis@osis-ai-toolkits
   ```

> marketplace 名称（`osis-ai-toolkits`）与 plugin slug（`osis`）发布后保持稳定，不要改。

## 更新插件

前提：发布方提高了 `plugin.json` 里的 `version`。**版本号不变，两家都不认为有更新。**

| 场景 | Claude Code | Codex |
|---|---|---|
| 从 GitHub 安装，自动 | `/plugin` → **Marketplaces** → 选 `osis-ai-toolkits` → **Enable auto-update**（第三方 marketplace 默认关，开一次即可）。之后每次启动后台拉取，当前会话提示 `/reload-plugins`，下次会话生效 | 无自动更新 |
| 从 GitHub 安装，手动 | `claude plugin update osis@osis-ai-toolkits`（只跑 `claude plugin marketplace update` 不会更新已装插件） | `codex plugin marketplace upgrade`（会一并更新已装插件） |
| 离线 | 新 zip 解压**覆盖**到原目录，再 `claude plugin update osis@osis-ai-toolkits` | 新 zip 解压覆盖到原目录，再 `codex plugin add osis@osis-ai-toolkits` |

更新后重开会话生效。

## 卸载

```text
:: Claude Code
claude plugin uninstall osis@osis-ai-toolkits
claude plugin marketplace remove osis-ai-toolkits     :: 可选，连同 marketplace 一起删

:: Codex
codex plugin remove osis@osis-ai-toolkits
codex plugin marketplace remove osis-ai-toolkits      :: 可选
```

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
uv pip install osis_broker-1.0.6-py3-none-any.whl     :: 由 osis-broker 仓库 uv build 产出
osis-broker --debug
:: 目标机器没有 pyosis 时:  uv pip install "osis-broker[pyosis]"
```

正式发布阶段 Broker 随 OSIS 产品一起分发。

**WeKnora 知识库**（桥梁模板检索，可选）：插件以 `python -m weknora_mcp_server` 启动，
key 读环境变量 `WEKNORA_API_KEY`（Python 环境由 OSIS 环境初始化工具准备）。
连不上时领域 skill 自动降级到本地 `seedtpl` 模板。

**默认实例与失效规则**（手写脚本直接打 18080 时适用，详见 `osis-broker/docs/contract.md §2.4`）：

- 首个就绪实例自动成为默认目标；WebUI 顶部显示并可显式切换；
- 默认实例离线/关闭/移除 → **报错，绝不自动改用另一个模型**；
- 显式 `/instances/{id}/` 路由（`execute_python` 的 instance_id）不受切换影响；
- 不跨 Broker 重启持久化，重启后由首个就绪心跳重新绑定。

**CORS 实际策略**（与 `osis-broker/README.md` 一致）：精确白名单 + `127.0.0.1`/
`localhost` 任意端口 + `osisbim.com` 子域；非白名单来源服务端 403；设置
`OSIS_BROKER_TOKEN` 后跨源浏览器请求需 Bearer，同源 WebUI 与无 Origin 原生调用豁免。

## 更新领域 skill

领域 skill 的唯一源是 `osis-skill-enhance/.agents/skills`（与 OSIS-AI 共用）。在那边改完后：

```bat
python scripts\sync_skills.py
```

## 发布新版本

1. `python scripts\sync_skills.py` 同步 skill（源仓库先提交，`.synced-from` 才不带 `dirty`）。
2. 两处版本号一起改：`plugins/osis/plugin.json`、`plugins/osis/.claude-plugin/plugin.json`。
3. 跑测试（见下），提交并 push —— 在线用户据此更新。
4. 给离线用户打 zip（只含已提交内容）：

   ```bat
   git archive --format=zip --prefix=osis-ai-toolkits/ -o dist\osis-ai-toolkits-<版本>.zip HEAD
   ```

   Broker wheel 另行分发（见 [使用前提](#使用前提)）。

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
