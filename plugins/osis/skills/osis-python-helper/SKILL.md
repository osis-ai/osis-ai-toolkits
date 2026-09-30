---
name: osis-python-helper
description: >
  基于 pyosis 回答问题或辅助生成建模代码。当用户需要 (1) 生成 pyosis 代码、
  (2) 查询某个 pyosis Manager/API 用法、(3) 解决 pyosis 使用中的报错时使用本技能。
  查签名/参数时优先调 MCP 工具 get_api_help(支持中文查询);
  get_api_help 查不到或版本不符时立即降级到本 SKILL 的 scripts/pyosis_doc.py。
  禁止把 SKILL 列表当成知识库;禁止默认通读 manager.py;仅 lookup 不够或需看实现细节时再打开源码。
---

# pyosis 助手

pyosis 是 OSIS 的 Python 建模库(Manager 模式),通过 HTTP 控制运行中的 OSIS(须已启动登录)。
所有 API 以当前安装版本为准,不确定就现场查,禁止凭印象写。

> **端口与执行方式(Codex / Claude Code)**:你不需要、也不应该自己去连 OSIS 端口。
> 所有 Python 都通过 MCP 工具 `execute_python(instance_id, code 或 file)` 执行,
> Broker 在 OSIS 官方 Python 环境里子进程运行,端口与 `instance_id` 的映射由
> OSIS Agent Broker 维护(注意:Broker 自己监听 18080,
> 那是 Broker 而不是 OSIS)。需要查 API 用 `get_api_help`。

## 安装

```bash
python -m pip install osis-python   # PyPI 包名是 osis-python,不是 pyosis
```

## 核心模式

```python
from pyosis.engine import OSISEngine
engine = OSISEngine()

engine.material.create_conc(no=1, name="C30", code="JTG3362_2018", grade="C30")
engine.node.create(no=1, x=0, y=0, z=0)
engine.element.create(no=1, type="BEAM3D", node1=1, node2=2, nMat=1, nSec1=1, nSec2=1)

lc = engine.load.create("自重", "CS", 1.0)   # manager 层:创建荷载工况
lc.create("GRAVITY")                          # 对象层:向工况加荷载——两个 create 不是一回事

engine.solve()
```

- Manager 一律经 `engine.<name>` 访问:material / section / node / element / boundary / load / tendon(含 prop、shape)/ stage / live / settlement / stability / dynamic / post / result / control / geometry / prop / thickness / project。
- 各 Manager 有通用入口 `create(no, type, **kwargs)`,按 type 字符串转发到 `create_<type>`。
- `create` / `get` 返回 dataclass,操作下沉到对象(如 `lc.create_gravity()`、`grp.add(1, 2)`)。
- 源码在 `site-packages/pyosis/<module>/manager.py`(每模块单文件)。

## 查 API(现场查)

1. MCP 工具 `get_api_help`(query 支持中文 / symbol 精确查,拿到签名、参数、返回值、示例)
2. 拿不到或版本不符 → 本 SKILL 的 `pyosis_doc.py`(用法见下)
3. 仍不够才读源码 manager.py

## pyosis_doc.py 用法

CLI 从**当前 Python 环境**运行时反射已安装的 pyosis(只索引 `*.manager` / `*.engine` / `*.interface` / `*.static` 模块),输出签名 + 完整 docstring + 源码位置。路径写 `<skill_dir>/scripts/pyosis_doc.py`。

```bash
# 版本与索引规模(确认反射的是不是预期环境)
python pyosis_doc.py version

# 精确查:短名 / Class.method
python pyosis_doc.py lookup create_line_load
python pyosis_doc.py lookup LoadCase.create_line_load

# 口语路径也行(内部别名展开)
python pyosis_doc.py lookup tendon.prop.create_in
python pyosis_doc.py lookup prop.assign_component_thickness

# 荷载 TYPE 口语:自动映射到对应 create_*,并提示 lc.create('UTEMP', ...) 的转发关系
python pyosis_doc.py lookup UTEMP
python pyosis_doc.py lookup "load.create UTEMP"

# 同名多命中:退出码 2,先列候选(qual + 模块 + docstring 首行),再选
python pyosis_doc.py lookup create            # → 列出全部 create_* 候选
python pyosis_doc.py lookup create --all      # 全部展开

# 子串搜索(含 docstring 内容),--limit 默认 30
python pyosis_doc.py search thickness
python pyosis_doc.py search uniform --limit 20
```

- **命中输出**:`kind`(method/function/class/property/field)、`signature`、`source: 文件:行号`、完整 docstring;个别已知坑会附带 `hint:`(如 `create_in` 摩阻参数位序、`gradient_temp` 读回过滤),hint 优先于 docstring。
- **退出码**:0 命中;1 未找到(试短名、TYPE 或 search);2 多候选(加 `--all` 或改用 `Class.method` 精确指定)。
- 也可查读回属性/dataclass 字段,如 `lookup gradient_temp`。

## 关键坑(查签名看不出来的)

- **禁止 `engine.new_project`**——OSIS-AI 始终在已打开的项目里工作;保存用 `engine.save_project()`。
- PropertyManager 入口是 `engine.prop`,不是 `engine.property`。
- 第一参数约定:多数 `create_*` 第一参数是 `no=None`(自动分配);例外——`stage.create` 的 no 必填 int(编号须连续),`tendon.prop` / `tendon.shape` / `load` / `settlement` / `live` / `geometry` 的 create 第一参数是 `name`。
- 修改结构 = 同 `no` 重新 create 覆盖;新增 = 新 `no`。
- 局部改自重/节点力/PST 等标量也先改对应 `prep/_N.py`,再按 `osis-engine` 跑 `prep/main.py`。不要走已停用的 `osis-l0-hot`。
