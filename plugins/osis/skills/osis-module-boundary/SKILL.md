---
name: osis-module-boundary
description: 边界建模模块。生成 `prep/_7_boundary.py`,创建支座约束(一般支撑、主从约束、弹性支承、刚性连接),并按边界组管理激活/钝化。处理"组名 = 跨模块契约"——`_7` 创建的边界组被 `_10` 阶段激活引用。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-boundary

> 边界模块。负责把桥型层决定的支座方案转成边界对象,按用途建边界组,供 `_10` 阶段激活。

## 接到任务后,按顺序做

1. **从桥型层读取支座方案**:支座位置(节点)、约束方向、临时/永久约束、体系转换时序。
2. **创建边界对象**(`create_general` / `create_master_slave` / `create_elstcspt` / `create_rigid`),显式指定 `no=` 编号。
3. **分配边界到节点**(`boundary.assign(op, *nodes)`)。
4. **组建边界组**(`boundary.group.create`),让 `_10` 阶段按名激活。
5. **把边界编号、组名写入建模状态**(`boundaries` 字段)。

## 公共约定

所有 `create_*` 方法的**第一个位置参数都是 `no`(边界编号)**,不是 `node` 或 `entity`。`no` 可显式传,也可传 `None` 让 OSIS 自动分配。

## 5 种边界类型

| 类型 | API | 用途 |
|---|---|---|
| `GENERAL` | `create_general` | 一般支撑(7 个自由度 0/1 约束) |
| `MSTSLV` | `create_master_slave` | 主从约束(墩梁固结等) |
| `ELSTCSPT` | `create_elstcspt` | 弹性支承(每方向 flag + 刚度) |
| `GES` | `create_general_elstcspt` | 一般弹性支承(6×6 刚度矩阵) |
| `RIGID` | `create_rigid` | 刚性连接(刚性区域) |
| `RELEASE` | `create_release` | 释放梁端约束 |

## 通用入口

```python
engine.boundary.create(no, type, *args, **kwargs)
```

按 `type` 派发到具体 `create_*`。

**`create_*` 与 `create()` 的关系**:两者只差一个 `type` 路由参数,其余参数(顺序、含义、默认值)完全一致——`create_*` 等价于 `create()` 帮你填好了 `type`。例:`create(1, "GENERAL", x=1, y=1)` ≡ `create_general(1, x=1, y=1)`;`create(2, "MSTSLV", node=5)` ≡ `create_master_slave(2, node=5)`。日常推荐 `create_*`;`create()` 适合按配置表/循环动态派发。

## 一般支撑 `create_general`

7 个自由度,每个 0=释放 / 1=约束(0/1 标志):

```python
b = engine.boundary.create_general(
    no,                          # 边界编号
    coor="",                     # 局部坐标系编号(空 = 缺省)
    x=1, y=1, z=1,               # 平动 UX/UY/UZ(0/1)
    rx=1, ry=1, rz=1,            # 转动 RX/RY/RZ(0/1)
    rw=1,                        # 翘曲 RW(0/1,7 个自由度)
)
```

**`x/y/z/rx/ry/rz/rw` 是 0/1 标志**。

**应用示例**:
- 桥台固定端:`x=1, y=1, z=1, rx=1, ry=0, rz=0`(纵桥向可滑动)
- 桥墩活动端:`z=1, 其余 0`

## 主从约束 `create_master_slave`

主从约束把当前节点(从节点)的所有自由度绑到 `node` 指定的主节点:

```python
b = engine.boundary.create_master_slave(
    no,                          # 边界编号
    node,                        # 主节点编号
    dx=1, dy=1, dz=1,            # 平动自由度(0/1)
    rx=1, ry=1, rz=1,            # 转动自由度(0/1)
    coincident=1,                # 主从是否共点(0/1)
)
```

**应用**:刚构墩梁固结(主=桥墩顶节点,从=主梁节点)。

## 弹性支承 `create_elstcspt`

每个方向是 **启用标志 + 刚度值** 的成对参数,共 7 对:

```python
b = engine.boundary.create_elstcspt(
    no,                          # 边界编号
    coor="",                     # 局部坐标系编号
    x=1,  dx=1e13,               # UX:启用 + 刚度
    y=1,  dy=1e13,               # UY
    z=1,  dz=1e13,               # UZ
    rx=1, drx=1e16,              # RX(刚度极大值 = 固定)
    ry=1, dry=1e16,              # RY
    rz=1, drz=1e16,              # RZ
)
```

**刚度极大值 = 固定**:平动 `1e13`,转动 `1e16`。

## 刚性连接 `create_rigid`

```python
b = engine.boundary.create_rigid(no, nNodeI)   # nNodeI 为主节点
```

形成刚性区域:从 `nNodeI` 出发,通过 `boundary.assign` 添加其它从节点。

## 分配边界到节点

`create_*` 之后,边界只是定义;要让它生效必须分配到节点:

```python
b.assign(
    op,                          # 'a'=添加(默认) / 's'=替换 / 'r'=移除 / 'aa'=全加 / 'ra'=全删
    1, 2, 3, 4, 5,              # 节点编号 varargs(也可传单个 list 或 "2to4")
)
```

`op` 有默认值 `"a"`,但**建议始终显式传**,避免误读;节点编号是 varargs。

**禁止传入 Python `set`**:`assign("a", {64})` 会把命令写成 `AsgnBd,11,a,{64}`,OSIS 弹「非法输入：{64}」,边界看起来写入了、节点上其实没有。正确写法:`assign("a", 64)` 或 `assign("a", "2to4")` 或 `assign("a", [2, 3, 4])`。CS1 报「未定义边界条件 / 边界未定义在已激活单元上」时,先查 `_7` 是否把 set 写进了 `assign`。

## 边界组 = 阶段激活契约(核心规则)

**`_7` 创建的边界组,被 `_10` 阶段激活引用**:

```python
bg = engine.boundary.group.create(name, "c")  # op 必填
```

`bg.add(1, 2, 3)` / `bg.remove(4)` / `bg.replace(5, 6)` / `bg.rename("新名")`

`op` 必填,常见值:`"c"`(创建)、`"a"`(添加)、`"s"`(替换)、`"r"`(移除)、`"aa"`(全加)、`"ra"`(全删)、`"m"`(改名)、`"d"`(删除)。

> **两种写法等价**:`bg = create(name, "c"); bg.add(...)` 与 `create(name, "c"); create(name, "a", ...)` 底层是同一条 `BdGrp` 命令。`create(name, "a", 2, 4)`(varargs)和 `create(name, "a", [2, 4])`(list)等价,**推荐用 varargs 形式**;`bg.add(2, 4)` 无此限制(内部自动打包成 list)——**优先用 `create(name, "c")` + `bg.add(...)`**。注意 **`add` 在返回的 `BoundaryGroup` 对象上,manager 上没有 `add`**——`engine.boundary.group.add(...)` 会抛 `AttributeError`。element.group 无此坑(其底层接口本身就是 varargs)。

> **`create(name, "c")` 不是幂等的**:同名边界组已存在时再 `"c"` 会报"已经存在"。单模块重跑前先 `if engine.boundary.group.get(name): engine.boundary.group.delete(name)`(组删除无依赖检查,可直接用),或改用 `"s"`(替换)语义。详见 `osis-engine/references/incremental_rerun.md`。

阶段激活引用示例(`_10_stage` 模块):
```python
stg.define_boundary(1, 1, "桥墩永久约束组")  # op=1(add), type=1(activate)
```

**组名逐字一致**。

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `boundaries` 字段(边界编号、约束向量、边界组清单、体系转换时序)。

## 失败模式

- **下游报"组不存在"** —— `_10` 引用的边界组名在本 module 没建,或名字差一字符
- **约束方向错** —— 7 个自由度错位(尤其 `rx/ry/rz` 与 `rw` 翘曲)
- **墩梁固结失真** —— `create_master_slave` 没设 `coincident=1`
- **弹性支承"弹性连接报错"** —— 刚度值过小(应该 `1e13/1e16`)
- **`非法输入：{64}` / `AsgnBd,...,{n}`** —— `assign` 传了 Python `set`;改成 int / `"a,bto c"` / list 后 L1 重跑 `_7`
- **`Solve` / CS1「未定义边界条件,或者边界条件未定义在已激活单元上」** —— 阶段激活了 0 号块,但墩顶临时支架没挂到已激活节点(常见就是上一则 set 写法,或临时支架挂在未激活的桥台节点上)

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 桥型层 → 本模块 | 支座方案(类型、节点、临时/永久、体系转换时序) |
| 上游 `osis-module-node` | 桥墩/桥台节点编号(边界 assign 引用) |
| 下游 `osis-module-stage` | 边界组名(阶段 `define_boundary` 引用) |

**组名 = 跨模块契约**(见 osis-engine §会话硬约束):`_10` 阶段 `define_boundary` 的 `group_name` 必须等于本 module 创建的组名,差字符报"组不存在"。
