# AGENTS.md — 维护者说明

用户文档见 `README.md`；本文件写给维护本仓库的人和 Agent。

一个 Git 仓库同时服务 **Codex** 和 **Claude Code**：共享同一份 Skill、同一个 MCP endpoint、同一套测试，只针对不同宿主维护很薄的 manifest 适配。插件只连本机 `http://127.0.0.1:18080/mcp`（服务端在 `osis-broker` 仓库，通信契约见 `osis-broker/docs/contract.md`）。

## 仓库结构

```text
osis-ai-toolkits/
├── .agents/plugins/marketplace.json      Codex marketplace
├── .claude-plugin/marketplace.json       Claude Code marketplace
└── plugins/osis/
    ├── plugin.json            Codex 便携 manifest
    ├── mcp.json               Codex MCP 配置(osis + weknora)
    ├── .claude-plugin/plugin.json  Claude Code manifest
    ├── .mcp.json              Claude Code MCP 配置(同上,格式不同)
    ├── skills/                Codex / Claude 共用
    │   ├── osis-engine/       ┐
    │   ├── osis-bridge-*/     │ 领域 skill:从 osis-skill-enhance
    │   ├── osis-module-*/     │ 原样同步(scripts/sync_skills.py),
    │   └── ...                ┘ 不要在本仓库手改
    ├── README.md
    └── tests/                 manifest、同步一致性校验
scripts/sync_skills.py         同步领域 skill
```

marketplace 名称（`osis-ai-toolkits`）与 plugin slug（`osis`）发布后保持稳定，不要改。

## 更新领域 skill

领域 skill 的唯一源是 `osis-skill-enhance/.agents/skills`（与 OSIS-AI 共用）。在那边改完并提交后：

```bat
python scripts\sync_skills.py
```

源仓库未提交时 `.synced-from` 会标 `(dirty)`。

## 发布新版本

1. 同步 skill（见上）。
2. 两处版本号一起改：`plugins/osis/plugin.json`、`plugins/osis/.claude-plugin/plugin.json`。**版本号不变，Claude Code / Codex 都不认为有更新。**
3. 跑测试（见下），提交并 push —— 在线用户据此更新。
4. 给离线用户打 zip（只含已提交内容）：

   ```bat
   git archive --format=zip --prefix=osis-ai-toolkits/ -o dist\osis-ai-toolkits-<版本>.zip HEAD
   ```

更新行为实测（2026-10）：

- Claude Code：`claude plugin marketplace update` 只刷新清单，不更新已装插件；更新插件用 `claude plugin update`。第三方 marketplace 自动更新默认关。
- Codex：`codex plugin marketplace upgrade` 会一并更新已装插件；本地目录 marketplace 需重新 `codex plugin add`。
- 两家都不能直接装 zip，只接受目录 / git / GitHub 源。

## 测试

```bat
%USERPROFILE%\.osisai\.venv\Scripts\python.exe -m pytest plugins/osis/tests -q
```

覆盖：两侧 marketplace 结构、manifest 字段、MCP endpoint 一致性、端口全仓一致性、Skill 完整性、与源仓库同步一致；若本机服务正在运行，额外验证 MCP 可连。

## 相关仓库

| 仓库 | 职责 |
|---|---|
| `osis-ai-toolkits`（本仓库） | MCP 配置、Skill、Codex / Claude 插件 |
| `osis-skill-enhance` | 领域 skill 唯一源 |
| `osis-broker` | 本机 MCP 服务端：实例注册、代理、MCP Server、API 文档检索、WebUI |
| `osis-python-runtime` | `runtime-bootstrap`：准备 `~/.osisai/.venv` |
