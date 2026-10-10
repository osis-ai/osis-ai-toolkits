# OSIS AI Toolkits

让 **Codex**、**Claude Code** 等 Agent 直接操作 [OSIS 桥梁设计分析软件](https://www.osisbim.com/osis/home/) 的插件。

安装后，你可以直接在 Codex / Claude Code 里说：

> 检查当前模型并帮我修改材料参数，然后运行计算。

## 使用前提

- OSIS 版本 **> 5.01**
- 使用时 OSIS 已打开
- OSIS 的 Python 环境 `%USERPROFILE%\.osisai\.venv` 里装有 osis-broker **≥ 1.0.12**（插件靠它启动 MCP，不用手动启动 Broker）

> **首次使用前，先打开一次 OSIS，等它自动装好 Python 环境（`%USERPROFILE%\.osisai\.venv`）再启用本插件。** 插件的 MCP 全靠这个环境里的 Python 启动；环境没装好，Agent 里会显示 MCP 启动失败或没有 OSIS 工具。遇到这种情况，打开 OSIS 等环境装完，再重开 Agent 应用即可。

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
codex plugin add osis@osis-ai-toolkits
```

也可以在 Codex 的 `/plugins` 中安装 **OSIS**。

### 其他平台

| 平台 | 安装 |
|---|---|
| ZCode | 设置 → 插件 → 创建 → 添加市场，填 `osis-ai/osis-ai-toolkits`，再装 **osis** |
| WorkBuddy / CodeBuddy | `codebuddy plugin marketplace add osis-ai/osis-ai-toolkits`，再 `codebuddy plugin install osis@osis-ai-toolkits` |
| Qoder CLI | `qodercli plugins marketplace add osis-ai/osis-ai-toolkits`，再 `qodercli plugins install osis` |
| Qoder IDE | 把 `plugins/osis` 目录**里面的内容**打成 zip（zip 根目录直接是 `.qoder-plugin/`），扩展 → 插件 → 添加插件 → 上传插件 |
| Kimi Code | `/plugins install https://github.com/osis-ai/osis-ai-toolkits` |
| MiniMax Code | 插件 → 导入，选 GitHub 目录 `osis-ai/osis-ai-toolkits` 下的 `plugins/osis`，或把该目录内容打成 zip 导入（zip 根目录直接是 `.minimax-plugin/`） |
| Trae / 豆包桌面版 | 没有插件机制，按下面手动配 |

**Trae / 豆包桌面版手动配置**（先按下文「离线安装」第 1、2 步拿到 `D:\osis-ai-toolkits-main`）：

1. 技能：
   - Trae：把 `plugins\osis\skills` 下的各技能目录拷到 `%USERPROFILE%\.trae-cn\skills`（国际版为 `%USERPROFILE%\.trae\skills`）：
     `xcopy /E /I /Y D:\osis-ai-toolkits-main\plugins\osis\skills %USERPROFILE%\.trae-cn\skills`
   - 豆包：技能 · 连接器 · 伙伴 → 我的技能 → 新建 → 上传技能，逐个上传 `plugins\osis\skills` 下的技能目录。
2. MCP：
   - Trae：设置 → MCP → 添加 → 手动配置，粘贴下面的 JSON。
   - 豆包：技能 · 连接器 · 伙伴 → 新建 → 新建自定义连接器，传输类型选 STDIO，按下面 JSON 每个 server 各建一个（命令 `cmd`，参数和环境变量照填）。

```json
{
  "mcpServers": {
    "osis": {
      "command": "cmd",
      "args": ["/c", "%USERPROFILE%\\.osisai\\.venv\\Scripts\\python.exe", "-P", "-m", "osis_broker", "--stdio"]
    },
    "weknora": {
      "command": "cmd",
      "args": ["/c", "%USERPROFILE%\\.osisai\\.venv\\Scripts\\python.exe", "-P", "-m", "weknora_mcp_server"],
      "env": { "WEKNORA_BASE_URL": "https://knowledge.osisbim.com/api/v1" }
    }
  }
}
```

### 离线安装（zip）

适合命令行连不上 GitHub 的电脑。Claude Code 和 Codex 都**不能直接装 zip**，必须先解压：

1. 下载最新版 zip：<https://github.com/osis-ai/osis-ai-toolkits/archive/refs/heads/main.zip>（能上 GitHub 的电脑下好再拷过去也行）。
2. 解压到**固定位置**，如 `D:\`，得到 `D:\osis-ai-toolkits-main`（之后更新要覆盖到同一目录，别删）。
3. 安装：

   ```text
   :: Claude Code
   claude plugin marketplace add D:\osis-ai-toolkits-main
   claude plugin install osis@osis-ai-toolkits

   :: Codex
   codex plugin marketplace add D:\osis-ai-toolkits-main
   codex plugin add osis@osis-ai-toolkits
   ```

## 更新

| 场景 | Claude Code | Codex |
|---|---|---|
| 在线，自动 | `/plugin` → **Marketplaces** → 选 `osis-ai-toolkits` → **Enable auto-update**（默认关，开一次即可）。之后每次启动自动检查，下次会话生效 | 不支持自动更新 |
| 在线，手动 | `claude plugin update osis@osis-ai-toolkits` | `codex plugin marketplace upgrade` |
| 离线 | 重新下载上面的 zip，解压**覆盖**到原目录，再 `claude plugin update osis@osis-ai-toolkits` | 新 zip 解压覆盖到原目录，再 `codex plugin add osis@osis-ai-toolkits` |

其他平台在各自的插件管理页更新。更新后重开会话生效。

## 卸载

```text
:: Claude Code
claude plugin uninstall osis@osis-ai-toolkits
claude plugin marketplace remove osis-ai-toolkits     :: 可选，连同 marketplace 一起删

:: Codex
codex plugin remove osis@osis-ai-toolkits
codex plugin marketplace remove osis-ai-toolkits      :: 可选
```

其他平台在各自的插件管理页卸载。

## 可选：知识库

插件自带桥梁模板；自带模板里找不到时，会再查 WeKnora 知识库。向管理员要访问 key，设成 Windows 环境变量 `WEKNORA_API_KEY`：

- 开始菜单搜「编辑系统环境变量」→ 环境变量 → 新建，变量名 `WEKNORA_API_KEY`，值填 key；
- 或在命令行执行 `setx WEKNORA_API_KEY 你的key`。

设好后**完全退出并重开** Agent 应用（Claude Code、Codex、ZCode 等），新值才会生效。

不设置插件也能正常打开，只是知识库查不了。
