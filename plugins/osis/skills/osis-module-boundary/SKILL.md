---
name: osis-module-boundary
description: 边界建模模块。生成 `prep/_7_boundary.py`,创建支座约束(一般支撑、主从约束、弹性支承、刚性连接),并按边界组管理激活/钝化。处理"组名 = 跨模块契约"——`_7` 创建的边界组被 `_10` 阶段激活引用。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-boundary

> 边界模块。负责把桥型层决定的支座方案转成边界对象,按用途建边界组,供 `_10` 阶段激活。

## 接到任务后,按顺序做

1. **从桥型层读取支座方案**:支座位置(节点)、约束方向、临时/永久约束、体系转换时序。
2. **创建边界对象**,显式指定 `no`(第一个位置参数,不是节点号)。
3. **分配边界到节点**(`b.assign(op, *nodes)`)。
4. **组建边界组**(`boundary.group.create`),让 `_10` 阶段按名激活。
5. **把边界编号、组名写入建模状态**。

## 选边界类型

常用的几种(完整类型与参数用 `api_grep "def create_" boundary` / `api_read` 查):

| API | 用途 | 要点 |
|---|---|---|
| `create_general` | 一般支撑 | `x,y,z,rx,ry,rz,rw` 7 个 0/1 标志,1=约束、0=释放 |
| `create_master_slave` | 主从约束(墩梁固结等) | 主=桥墩顶节点,从=主梁节点;`coincident=1`(默认)含转动耦合,`0` 只同位移 |
| `create_elstcspt` | 弹性支承 | 每方向"启用标志 + 刚度"成对;固定用平动 `1e13`、转动 `1e16` |
| `create_rigid` | 刚性连接 | `create_rigid(no, node_i)`,`node_i` 为主节点,从节点经 `assign` 加入 |

支座约束向量写法(x,y,z,rx,ry,rz,rw):固定支座 `1,1,1,1,0,1,0`(释放绕 Y 的竖向弯曲转角和翘曲);纵向滑动支座再放开 x:`0,1,1,1,0,1,0`。

## 分配边界到节点

`create_*` 之后边界只是定义,必须分配到节点才生效:

```python
b.assign("a", 1, 2, "5to9")   # op: 'a' 添加 / 's' 替换 / 'r' 移除 / 'aa' 全加 / 'ra' 全删;节点 varargs、list 或 "MtoN"
```

- `op` 有默认值 `"a"`,建议始终显式传。
- **禁止传 Python `set`**:`assign("a", {64})` 会写成 `AsgnBd,11,a,{64}`,OSIS 弹「非法输入：{64}」,边界看似写入、节点上其实没有。

## 边界组 = 阶段激活契约

`_7` 创建的边界组被 `_10` 的 `define_boundary` 按名引用,组名必须逐字一致。

```python
if engine.boundary.group.get(name):
    engine.boundary.group.delete(name)   # 组删除无依赖检查,可直接用
bg = engine.boundary.group.create(name, "c")   # op 必填
bg.add(1, 2, 3)
```

- `create(name, "c")` 不幂等,同名已存在报"已经存在",所以先 delete-if-exists(见 `osis-engine/references/incremental_rerun.md`)。
- `add/remove/replace/rename` 在返回的 `BoundaryGroup` 对象上;manager 上没有 `add`,调了抛 `AttributeError`。
- 等价写法 `create(name, "a", 2, 4)` 与 `bg.add(2, 4)` 是同一条 `BdGrp` 命令。

## 失败模式

- **下游报"组不存在"** —— `_10` 引用的边界组名在本模块没建,或名字差一字符
- **约束方向错** —— 7 个自由度错位(尤其 `rx/ry/rz` 与 `rw` 翘曲)
- **墩梁固结失真** —— `create_master_slave` 把 `coincident` 设成了 0(只同位移,不耦合转动)
- **弹性支承"弹性连接报错"** —— 刚度值过小(固定应为 `1e13/1e16`)
- **`非法输入：{64}` / `AsgnBd,...,{n}`** —— `assign` 传了 Python `set`;改成 int / `"2to4"` / list 后写回
- **`Solve` / CS1「未定义边界条件,或者边界条件未定义在已激活单元上」** —— 阶段激活了构件,但它的支座/临时支架挂在未激活的节点上;或上一条的 set 写法导致边界没分配上

(其他见 `osis-engine/references/error_diagnosis.md`)
