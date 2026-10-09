---
name: osis
description: OSIS 桥梁有限元建模的总入口（Codex / Claude Code 版）。当用户要求查看/操作本机 OSIS 模型、建桥、改模型参数、加荷载或阶段、求解、查结果、生成计算书，或 OSIS Python API 报错需要定位时，先用本 SKILL。它规定如何选实例、查 API、写 Python、通过 OSIS Agent Broker 执行并验证结果。不涉及 OSIS 的具体建模规则——那些在 osis-engine / osis-bridge-* / osis-module-* 里。
---

# osis — OSIS Agent 总入口

> 你通过 **OSIS Agent Broker**（本机 `http://127.0.0.1:18080`）操作 OSIS。
> 实例列表里能直接看到端口字段（仅作信息展示）；但**连接与操作永远走 Broker**——用 `instance_id` / `execute_python`，不写直连端口的代码。
>
> `execute_python` 的执行模型：Broker 起 OSIS 官方 Python 子进程，子进程请求经
> **Broker 的指定实例路由**（`/instances/{instance_id}/`）转发到目标实例。
> **不要**让生成的 Python 自己填实例 ID 或真实端口 —— 目标完全由
> `execute_python(instance_id=...)` 决定。

## 0. MCP 工具

| 工具 | 用途 |
|---|---|
| `list_instances` | 列出当前可用的 OSIS 实例 |
| `get_instance_info` | 查单个实例的项目、版本、状态，操作前二次确认 |
| `api_glob` / `api_grep` / `api_read` | 查真实的 pyosis API —— 像 glob / grep / read 一样用（§1.2） |
| `execute_python` | 在指定实例里执行 Python —— 核心工具 |
| `raw_http_request` | 高级兼容入口，透传 OSIS HTTP API。**默认不用** |

工具是远程 HTTP MCP，服务端在 Broker。**调用前先确认 Broker 可连**：若 MCP 连接失败，直接告诉用户

```
OSIS Agent Broker 当前不可连接。
请确认 OSIS Agent 服务已启动。
```

不要提示用户去手动找 OSIS 实例端口，也不要自己猜测端口。

## 1. 标准工作流

```
用户提出 OSIS 操作
      ↓
list_instances  →  确定 instance_id
      ↓
判断是否熟悉该 API
      ├─ 不确定 ──→ api_glob / api_grep 定位 → api_read 看全文
      ↓
生成尽量短且明确的 Python
      ↓
execute_python(instance_id, code?/file?, cwd?, timeout?)
             instance_id="solver" → 仅求解器模式(OSIS 未启动也能用)
             instance_id="default" → 当前默认实例(与手写 18080 直连同目标)
      ↓
读 stdout / result / exception
      ├─ 有 exception → 修代码（必要时 api_read）→ 重试
      ↓
修改型任务：再查一次并验证结果
      ↓
向用户报告（含实例、做了什么、验证结果）
```

### 1.1 选实例

- **MCP 不保存 `current_instance`**。所有执行与修改调用都**显式**带 `instance_id`。
- 只有一个实例 → 直接用它。
- 多个实例 → 优先按 `project`、`window_title`、`state` 判断用户指的是哪个。
- 仍有歧义 → **必须问用户**，禁止随便挑一个。
- 实例重启后 `instance_id` 会变，**旧 ID 不得自动映射**到新实例；ID 失效就重新 `list_instances`。
- 端口字段可见，但不要主动向用户罗列；操作一律经 Broker（`instance_id` 路由 / `execute_python`），不绕过 Broker 直连。
- **没有启动任何 OSIS 实例也可以干活**：一次性求解（仅求解器模式）用魔法值
  `instance_id="solver"`，见 §1.4；`list_instances` 为空时不必让用户先开 OSIS。
- **魔法值 `instance_id="default"`**（大小写不敏感）= 路由到当前默认实例，
  与手写脚本直连 18080 是同一目标；默认实例失效时报结构化错误、**不自动换
  目标**（需在 WebUI 顶部或卡片上手动切换）。多实例歧义**不能**用它回避询问。
### 1.2 查 API

**不允许猜测 OSIS API 名称。** 不确定就先查：

```text
api_glob("engine.element.create_*")       列成员 / 按名找(通配符,不区分大小写)
api_grep("梁单元")                         正则逐行搜签名与 docstring,中文概念用它
api_read("engine.element.create_beam3d")  单个 API 全文:签名、参数、docstring、源码位置
```

- 索引来自 OSIS 执行环境里真实 `pyosis` 包的签名与 docstring，与 `execute_python` 跑的版本一致。
- `api_glob` 同时匹配限定名（`NodeManager.*`）和访问路径（`engine.tendon.prop.*`）；返回 `限定名(签名)  # 首行说明`。`*` 不跨 `.`：`engine.prop.*` 只列直接成员，整棵子树用 `engine.prop.**`；不含 `.` 的模式（`*load*`）也匹配方法短名。
- `api_grep` 把多处共用的同一句 docstring 合并成一条 `限定名1, 限定名2: 命中行`。
- `api_read` 接受限定名、`engine.x.y` 路径、唯一短名；类会附成员列表。
- 同名歧义（如 `create`）或找不到 → `API_HELP_NOT_FOUND` + `candidates`，从中挑限定名再读；**不要因此断言 OSIS 不支持该功能**。

### 1.3 写 Python

- 一次只做一个明确任务，脚本尽量短。
- 起点固定为：

```python
from pyosis import OSISEngine
engine = OSISEngine()   # 自动连接当前打开的 OSIS 项目
```

- Manager 经 `engine.<name>` 访问：`material` / `section` / `node` / `element` / `boundary` / `load` / `tendon` / `stage` / `live` / `settlement` / `stability` / `dynamic` / `post` / `result` / `control` / `geometry` / `prop` / `thickness` / `project`。
- OSIS 是**状态化**的：模型数据在 OSIS 进程里，不在 `.py` 文件里。改 `.py` ≠ 模型已变。
- **查询与求解分开**：读状态用查询 API（`engine.model_summary()`、`engine.node.count()` 等）；
  **只有用户明确要求求解时**才调 `engine.solve()`。不要为查询去求解，更不要为查询跑整桥重建。

### 1.4 执行与写回

```text
execute_python(instance_id="A81F", code="...", timeout=60)
execute_python(instance_id="A81F", file="py/prep/main.py", cwd="D:/proj")  ← 跑已有脚本
```

- **两条执行通道**：领域 Skill 里写的终端 `python xxx.py`（如 `python <project_dir>/py/prep/main.py`）
  可以照做——本机 pyosis 默认连 18080，即 Broker，落到**默认实例**；
  **多实例、或需要指定目标实例时，一律改用 `execute_python(instance_id=...)`**。
  不碰 OSIS 的纯本地脚本（`seedtpl.py`、`docx_tool.py` 等）直接终端跑。
- `code` / `file` 二选一；`file` 相对 `cwd` 解析。
- `cwd` 默认 `~/.osisai`：涉及相对路径读写、同级模块导入、跑工程目录下的脚本时，
  显式传工程目录；不确定就用默认。
- Broker 在 OSIS 官方 Python 环境里子进程执行，目标实例由 `instance_id` 决定
  （请求经 Broker 实例路由，见文首执行模型），结果从 stdout 返回。
- **带 CLI 参数的脚本**：`file` 模式会重置 `sys.argv`，不能直接表达 `python x.py --arg`。
  用 `code` + `sys.argv` + `runpy` 配方：

```python
import sys, runpy
sys.argv = [r"D:/proj/scripts/helper.py", "--span", "30"]  # [脚本名, 参数...]
runpy.run_path(r"D:/proj/scripts/helper.py", run_name="__main__")
```

返回：

```json
{"ok": true, "instance_id": "A81F", "stdout": "...", "stderr": "",
 "result": null, "execution_time_ms": 328, "cwd": "C:\\Users\\...\\.osisai",
 "exception": null}
```

失败时 `ok=false` 并带 `exception`（`type` / `message` / `traceback`）——**读 traceback 改代码再重试**，一次失败不代表 OSIS 不支持。

**异常 / 超时后先读回，再决定重试**：`EXECUTION_TIMEOUT` 只表示本地子进程被停止，
**不代表 OSIS 端已受理的操作被撤销**，也不代表修改没生效。重试前先查询/读回实例
状态与模型数据确认实际结果，**不要**直接重跑创建/修改命令（可能重复创建或清空重建）。

**改了模型脚本必须写回**。按工程模板生成的 `py/prep/` 脚本，写回用全量重建：

```python
import runpy
runpy.run_path(r"<project_dir>/py/prep/main.py", run_name="__main__")
```

（`main.py` 自带幂等的 `sys.path` 引导，任何工作目录都能跑。）只求解不改模型时用 `engine.solve()`，不要跑 `main.py`。

#### 仅求解器模式（OSIS 未启动 / 一次性求解）

`instance_id="solver"`（魔法值，大小写不敏感）：**不注册、不管理实例**，Broker
分配一个空闲端口（避开 Broker 自己的 18080），跑完即结束。适用：用户没开
OSIS、只想要求解结果的一次性任务。

```python
import os
from pyosis.core.solver import OSISSolver
from pyosis import OSISEngine

solver = OSISSolver(osis_install_path=r"<OSIS安装根目录>",   # 目录下需有 PySolver.dll
                    port=int(os.environ["OSIS_SOLVER_PORT"]))  # Broker 分配,不要写死
engine = OSISEngine.from_solver(solver)
engine.run("...")
engine.solve()
```

- **端口必须读 `OSIS_SOLVER_PORT`**（结果里也回显 `solver_port`）—— Broker 分配的，写死会与 Broker 的 18080 或其它进程相撞；
- 同一端口也写进了 pyosis 官方变量 `OSIS_HTTP_PORT`（pyosis 不认识
  `OSIS_SOLVER_PORT`，后者只是 Broker 给脚本的传参通道，因为
  `OSISSolver` 不读环境变量、默认硬编码 18080），所以零参数 `OSISEngine()`
  也会直连该 solver；
- `OSIS_URL` 在此模式下**不注入**，`from_solver` 设的端口不会被劫到 Broker 路由；
- 模型数据在 solver 进程里，**跑完即丢**——不改磁盘工程、不写回、不跨调用保留状态；
- 长求解把 `timeout` 加大（最大 600）。

禁止在没执行写回时说「已完成 / 已改好」；未执行最多说「代码已改，正在执行写回」。用户明确要求 dry-run 除外。

### 1.5 验证

修改型任务执行后，**再查一次**确认生效，例如读回节点数、材料参数、单元组，或 `engine.model_summary()`。把验证结果写进完工报告。

## 2. 铁律

1. 不要猜测 OSIS API 名称。
2. 不确定 API 时先用 `api_glob` / `api_grep` / `api_read` 查。
3. 所有操作明确使用 `instance_id`。
4. 多实例有歧义时询问用户。
5. 优先通过 Python API 完成复杂操作。
6. 脚本尽量一次完成一个明确任务。
7. 修改模型后尽量查询并验证结果。
8. Python 异常时读取 traceback 后修正。
9. 不要因为一次失败就假设 OSIS 不支持该功能。
10. 端口信息可见（列表里就有），但连接与操作一律经 Broker 路由——不写绕过 Broker 直连真实端口的代码，也不主动向用户罗列端口。

## 3. 错误码与应对

工具失败会返回稳定的 `error.code`，据此决定下一步：

| code | 该怎么办 |
|---|---|
| `BROKER_UNAVAILABLE` | 告知用户启动 OSIS Agent 服务，停止尝试 |
| `INSTANCE_NOT_FOUND` | 重新 `list_instances`，ID 可能已过期 |
| `INSTANCE_OFFLINE` | 实例已离线，重新 `list_instances`；提示用户检查 OSIS 是否闪退 |
| `INSTANCE_NOT_READY` | 实例 `starting`/`closing`，稍后重试或询问用户 |
| `INSTANCE_MISMATCH` | 上游返回 409+INSTANCE_MISMATCH（**兼容性错误**：当前 OSIS 不再校验、不会发送）→ 重新 `list_instances` 再试 |
| `EXECUTION_TIMEOUT` | 脚本超时，拆小任务或加大 `timeout` 后重试 |
| `PYTHON_ERROR` | 读 traceback，改代码（必要时 `api_read` 看签名）后重试 |
| `OSIS_HTTP_ERROR` | OSIS 侧返回非 2xx，看响应内容判断是参数问题还是实例问题 |
| `API_HELP_NOT_FOUND` | 看 `candidates`（歧义/近似名），或换 `api_glob` / `api_grep` 再找；不要断言不支持 |

## 4. 建模领域知识在哪

`osis` 只管「怎么跟 OSIS 打交道」。具体建模规则在同插件的其他 Skill：

| 需求 | Skill |
|---|---|
| 任务分类、桥型路由、模块编排、写回规范 | `osis-engine` |
| 六种桥型方案（节点序列、组名、阶段） | `osis-bridge-*` |
| 模块层 API 用法与约束（`_1`..`_10`） | `osis-module-*` |
| pyosis 关键坑；无 `api_*` 工具时的 `pyosis_doc.py` | `osis-python-helper` |
| 荷载组合与规范验算 | `osis-check` |
| 生成计算书 | `osis-calcbook` |

这些 Skill 与 OSIS-AI 共用同一份源，写法宿主中立：

- 「提问工具」= 你所在宿主自带的结构化提问工具；没有就用普通文本列选项。
- WeKnora 知识库工具由本插件的 `weknora` MCP 提供（工具名带宿主前缀，按后缀认）；不可用时按 `osis-engine` 降级走 `seedtpl`。
- `<skill_dir>` = 对应 SKILL.md 所在目录。
- 领域 Skill 里的「查 API」一律用本插件的 `api_glob` / `api_grep` / `api_read`。

## 5. 参考资料

`skills/osis/references/`：

- `concepts.md` — 实例、Broker、状态化模型等基本概念
- `common-workflows.md` — 查询 / 修改 / 求解 / 写回的标准流程
- `troubleshooting.md` — 常见错误与排查
- `examples.md` — 端到端调用示例
