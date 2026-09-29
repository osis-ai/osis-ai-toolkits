---
name: osis-module-node
description: 节点建模模块。生成 `prep/_5_node.py`,沿主梁轴线显式逐个创建节点,以及桥墩/桥台节点的 y/z 偏置。节点编号被 `_6`/`_7`/`_8` 引用,必须显式 `no=`。本模块只负责"按 x 序列逐个建节点"和"按偏置建桥墩节点",**节点序列的具体分布模式由桥型层 SKILL 决定**。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-node

> 节点模块。按 x 序列逐个建节点,按 y/z 偏置建桥墩节点。具体节点分布模式由桥型层决定。

## 接到任务后,按顺序做

1. **从桥型层 SKILL 读取节点 x 序列**(主梁节点列表 + 桥墩节点列表)。
2. **逐个创建主梁节点**(`y=0, z=0`)。
3. **逐个创建桥墩/桥台节点**(按桥型层给的 y/z 偏置)。
4. **显式逐个创建节点**,传 `no=` 保证幂等。
5. **把节点编号、关键位置写入建模状态**(`nodes` 字段)。

> **节点分布模式(锚固段加密、节段端点、湿接缝范围等)由桥型层 SKILL 决定**,本模块只负责按给定的 x 序列逐个建节点。

## 公共约定

`node.create(no, x, y, z)` 的**第一个位置参数是 `no`**(节点编号)。`no` 可显式传,也可传 `None` 让 OSIS 自动分配。**显式传 `no` 是推荐做法**——重跑模块不冲突,下游按编号引用不乱。

```python
n = engine.node.create(
    no=1,                  # 节点编号(显式)
    x=0.0,                 # X 坐标
    y=0.0,                 # Y 坐标
    z=0.0,                 # Z 坐标
)
```

`create` 返回 `Node` 对象(含 `x`/`y`/`z`/`related_elements`/`related_boundaries` 等属性)。

## 主梁节点创建

```python
n = engine.node.create(no, x, y=0, z=0)   # 主梁节点 y=0、z=0
```

- 主梁节点 y=0、z=0(沿桥轴线)
- `no` **必须显式指定**,后续 `_6`/`_7`/`_8` 按编号引用
- 编号不强制连续 —— 可任意,但建议从小到大、有规律
- 不要用 OSIS 自动编号 —— 重跑时引用关系会乱

## 桥墩/桥台节点

桥墩/桥台节点 y/z 偏置由桥型层给定:

```python
n = engine.node.create(no, x, y_pier, z_pier)
```

| 部位 | y 偏置含义 | z 偏置含义 |
|---|---|---|
| 单柱墩 | 0 | 主梁底 z 坐标(z=0 在顶面,故为负) |
| 双柱墩 | ±y_pier(对称) | 主梁底 z |
| 桥台 | ±y_abut | 桥台底 z(更深,依桥台高度) |

**y 偏置**:桥墩中心相对主梁轴线的横向距离。**z 偏置**:主梁底板 z = `-h + 0`(z=0 在顶面),墩底更深依墩高。

## 查询与维护

```python
node = engine.node.get(no)        # 按编号查询
all_nodes = engine.node.all()     # 全部节点
engine.node.renumber(old, new)    # 改编号
engine.node.delete(no)            # 删除
engine.node.count()               # 总数
```

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `nodes` 字段(主梁/桥墩节点编号、x 范围)。

## 失败模式

- **`Uz >> 1e5`** —— 桥墩节点 z 偏置算错(未到主梁底板),弹性连接失真
- **钢束 `形状控制点坐标超出参照单元组范围`** —— 锚固段节点 x 不在钢束曲线 x 范围内。检查钢束端点 x 是否对应已建节点

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 桥型层 → 本模块 | **节点 x 序列**(主梁 + 桥墩)、y/z 偏置 |
| 本模块 → `osis-module-element` | 节点编号、x 坐标(单元 `node1`/`node2` 引用) |
| 本模块 → `osis-module-boundary` | 桥墩/桥台节点编号(边界 `assign` 引用) |
| 本模块 → `osis-module-loadcase` / `osis-module-tendon` | 锚固点节点(钢束端部 x) |
