# OSIS AI Toolkits

让 **Codex** 和 **Claude Code** 直接操作 OSIS 桥梁模型的插件。

安装后，你可以直接在 Codex / Claude Code 里说：

> 检查当前模型并帮我修改材料参数，然后运行计算。

## 使用前提

- OSIS 版本 **> 5.01**
- 使用时 OSIS 已打开

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

### 离线安装（无法访问 GitHub 的电脑）

两家都**不能直接装 zip**，必须先解压：

1. 把 `osis-ai-toolkits-<版本>.zip` 解压到**固定位置**，如 `D:\osis-ai-toolkits`（之后更新要覆盖到同一目录，别删）。
2. 安装：

   ```text
   :: Claude Code
   claude plugin marketplace add D:\osis-ai-toolkits
   claude plugin install osis@osis-ai-toolkits

   :: Codex
   codex plugin marketplace add D:\osis-ai-toolkits
   codex plugin add osis@osis-ai-toolkits
   ```

## 更新

| 场景 | Claude Code | Codex |
|---|---|---|
| 在线，自动 | `/plugin` → **Marketplaces** → 选 `osis-ai-toolkits` → **Enable auto-update**（默认关，开一次即可）。之后每次启动自动检查，下次会话生效 | 不支持自动更新 |
| 在线，手动 | `claude plugin update osis@osis-ai-toolkits` | `codex plugin marketplace upgrade` |
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

## 可选：知识库

桥梁模板检索使用 WeKnora 知识库，需设置环境变量 `WEKNORA_API_KEY`。不设置也能用，会改用插件自带的本地模板。
