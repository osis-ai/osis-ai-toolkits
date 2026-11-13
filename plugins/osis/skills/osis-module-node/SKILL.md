---
name: osis-module-node
description: 节点建模模块。生成 `prep/_5_node.py`,逐个创建主梁节点和桥墩/桥台节点。节点怎么分布由桥型层 SKILL 决定,本模块只管创建写法。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-node

> `prep/_5_node.py`:`build_nodes(engine)`。节点 x 序列、桥墩偏置由桥型层给。

```python
engine.node.create(no, x, 0.0, 0.0)          # 主梁节点:y=0、z=0
engine.node.create(no, x, y_pier, z_pier)    # 桥墩/桥台节点
```

- **`no` 显式传,不要用 `None` 自动编号**:`_6`/`_7`/`_8`/`_9` 按编号引用,自动编号重跑后会错位。
- **z=0 在主梁顶面**,主梁底 `z = -h`。支座/墩顶节点放在梁底,墩底按墩高更深。

## 失败模式

- **竖向位移异常大(`Uz >> 1e5`)** —— 桥墩节点 z 没落在主梁底,弹性连接失真
