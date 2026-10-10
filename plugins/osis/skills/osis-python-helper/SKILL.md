---
name: osis-python-helper
description: >
  pyosis 用法要点与查签名看不出来的坑。生成 pyosis 代码、解决 pyosis 报错、开发调用 pyosis 的独立 Python 项目时使用。
  具体签名/参数用 OSIS MCP 的 api_glob / api_grep / api_read 现场查,不要凭印象写,不要去知识库查 API。
  禁止默认通读 manager.py;api_* 不够或需看实现细节时再打开源码。
---

# pyosis 助手

pyosis 是 OSIS 的 Python 建模库(Manager 模式),通过 HTTP 控制已打开的 OSIS。
Agent 里的脚本经 OSIS MCP 的 `execute_python` 执行,连接由 Broker 注入,代码里不要自己指定端口;用户自己的独立项目见 §独立 Python 项目。

## 核心模式

```python
from pyosis import OSISEngine
engine = OSISEngine()

engine.material.create_conc(no=1, name="C30", code="JTG3362_2018", grade="C30")
engine.node.create(no=1, x=0, y=0, z=0)
engine.element.create(no=1, type="BEAM3D", node1=1, node2=2, mat=1, sec1=1, sec2=1)

lc = engine.load.create("自重", "CS", 1.0)   # manager 层:创建荷载工况
lc.create("GRAVITY")                          # 对象层:向工况加荷载——两个 create 不是一回事

engine.solve()
```

- Manager 一律经 `engine.<name>` 访问:material / section / node / element / boundary / load / tendon(含 prop、shape)/ stage / live / settlement / stability / dynamic / post / result / control / geometry / prop / thickness / project。
- 各 Manager 有通用入口 `create(no, type, **kwargs)`,按 type 字符串转发到 `create_<type>`。
- `create` / `get` 返回 dataclass,操作下沉到对象(如 `lc.create_gravity()`、`grp.add(1, 2)`)。

## 独立 Python 项目

用户开发自己的 Python 项目(如读外部数据库再建模)时,代码运行在用户自己的环境里,不经过 `execute_python`,交付的代码不依赖 MCP:

- **安装**:`uv add osis-python` 或 `pip install osis-python`,导入名是 `pyosis`。PyPI 上叫 `pyosis` 的是无关的包,不要装。和项目其他依赖(数据库驱动等)放在同一个环境,一个进程完成读库和建模。
- **连接**:零参数 `OSISEngine()` 即可,请求发到 Broker(`127.0.0.1:18080`,随 OSIS 启动),由 Broker 转给默认实例。运行前先打开 OSIS;代码里不写端口,不直连实例端口。
- **指定实例**:运行前设环境变量 `OSIS_URL=http://127.0.0.1:18080/instances/<instance_id>`(实例列表见 `GET http://127.0.0.1:18080/instances` 或 MCP `list_instances`);不设就是默认实例。
- **开发阶段**:签名用 `api_glob` / `api_grep` / `api_read` 查;代码片段先用 `execute_python` 在 OSIS 里试,再写进项目。
- **校核**:建模后读回校核(如 `engine.model_summary()`),不要只看脚本没报错。

## 查 API

签名、参数、docstring 用 OSIS MCP 的 `api_*` 工具现场查(索引来自 OSIS 执行环境里的 pyosis,与运行版本一致):
`api_glob` / `api_grep` 定位 → `api_read` 看全文 → 写代码。

- 荷载 TYPE 字符串(如 `UTEMP`)、中文概念用 `api_grep` 搜;`lc.create("UTEMP", ...)` 转发到对应的 `create_*`。
- `api_read` 遇同名歧义(如 `create`)返回 `candidates`,从中挑限定名再读,不要猜。
- 仍不够才读源码 `site-packages/pyosis/<module>/manager.py`(`api_read` 给出源码位置)。

## 关键坑(查签名看不出来的)

- **大量命令包在 `with pyosis.batch():` 里**:块内命令缓冲、退出时一次发送,快得多;块内查询会先自动冲刷;OSIS 报错抛 `BatchError`,调试可在块末尾 `pyosis.flush(isolate=True)` 定位坏命令。
- **禁止 `engine.new_project`**——始终在已打开的项目里工作;保存用 `engine.save_project()`。
- PropertyManager 入口是 `engine.prop`,不是 `engine.property`。
- `TendonPropManager.create_in` 位置序:name, mat, code, diameter, num, pipe, friction_coeff, deviation_coeff, …;便捷 `create` 是 name, s_type, mat, area 再接 create_in 余参。摩阻等系数的默认值是 1.0/0.0 占位,必须显式传。
- 很多荷载/边界参数默认值不是 0(如 `create_gravity` 的 `x_coeff`/`y_coeff` 默认 1.0、`create_spring` 刚度默认 10),用到的参数全部显式传。
- `lc.gradient_temp` 读回是 list[dict],按 `entityNO` 取单条,禁止 print 全表。
- 改构件厚度 `assign_component_thickness` 用 `op='a'`(再次调用即覆盖);`'s'` 在部分 OSIS 上报「编辑构件厚度有误」。
- 第一参数约定:多数 `create_*` 第一参数是 `no=None`(自动分配);例外——`stage.create` 的 no 必填 int(编号须连续),`tendon.prop` / `tendon.shape` / `load` / `settlement` / `live` / `geometry` 的 create 第一参数是 `name`。
- 修改结构 = 同 `no` 重新 create 覆盖;新增 = 新 `no`。
- 局部改自重/节点力/PST 等标量也先改对应 `prep/_N_xxx.py`,再按 `osis-engine` 的写回规则执行(单跑该模块或 `prep/main.py`)。
