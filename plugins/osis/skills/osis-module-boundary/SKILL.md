---
name: osis-module-boundary
description: 边界建模模块。生成 `prep/_7_boundary.py`,创建支座约束(一般支撑、主从约束、弹性支承、刚性连接)并建边界组,供 `_10` 阶段按名激活/钝化。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-boundary

> `prep/_7_boundary.py`:`build_boundaries(engine)`。支座方案(哪些节点、约束方向、临时/永久)由桥型层给。三步:建边界 → 分配到节点 → 建边界组。

## 边界类型

完整类型与参数用 `api_grep "def create_" boundary` / `api_read` 查。`create_*` 第一个位置参数是边界编号 `no`,不是节点号。

| API | 用途 | 要点 |
|---|---|---|
| `create_general` | 一般支撑 | `x,y,z,rx,ry,rz,rw` 7 个标志,1=约束、0=释放;**不传的方向默认约束** |
| `create_master_slave` | 主从约束(墩梁固结等) | 主=桥墩顶节点,从=主梁节点;`coincident=1`(默认)含转动耦合,`0` 只同位移 |
| `create_elstcspt` | 弹性支承 | 每方向"启用标志 + 刚度"成对;固定用平动 `1e13`、转动 `1e16` |
| `create_rigid` | 刚性连接 | `create_rigid(no, node_i)`,`node_i` 为主节点,从节点经 `assign` 加入 |

单梁模型的支座向量:固定支座 `1,1,1,1,0,1,0`(释放绕 Y 的弯曲转角和翘曲);纵向滑动支座再放开 x:`0,1,1,1,0,1,0`。

## 分配到节点

`create_*` 之后边界只是定义,分配到节点才生效:

```python
b.assign("a", 1, 2, "5to9")   # op: 'a' 添加 / 's' 替换 / 'r' 移除 / 'aa' 全加 / 'ra' 全删;节点 varargs、list 或 "MtoN"
```

**禁止传 Python `set`**:`assign("a", {64})` 会写成 `AsgnBd,11,a,{64}`,OSIS 弹「非法输入：{64}」,脚本不报错但节点上没有边界。

## 边界组

`_10` 的 `define_boundary` 按组名引用,组名逐字一致。

```python
if engine.boundary.group.get(name):
    engine.boundary.group.delete(name)          # 组删除无依赖检查,可直接用
bg = engine.boundary.group.create(name, "c")    # op 必填;不幂等,同名已存在报"已经存在"
bg.add(1, 2, 3)                                 # 边界编号
```

- `add/remove/replace/rename` 在返回的 `BoundaryGroup` 对象上;manager 上没有 `add`。
- `create(name, "a", 2, 4)` 与 `bg.add(2, 4)` 是同一条 `BdGrp` 命令。

## 失败模式

- **某方向位移 1e5 以上 / 机构** —— 约束向量 0/1 错位(尤其 `ry` 与 `rw`),或 `create_master_slave` 的 `coincident` 设成了 0
- **`非法输入：{64}`** —— `assign` 传了 set,改成 int / `"2to4"` / list
- **`Solve` 报「CSn:未定义边界条件,或者边界条件未定义在已激活单元上」** —— 该阶段激活的构件没有可用支承:支座/临时支架的节点不在本阶段已激活的单元上,或 `assign` 用了 set 没写进去
- **`弹性连接报错`** —— 弹性支承刚度过小;弹簧单元的情况见 `osis-module-element`
