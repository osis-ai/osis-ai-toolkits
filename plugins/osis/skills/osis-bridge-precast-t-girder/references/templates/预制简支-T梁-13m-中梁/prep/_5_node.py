"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.5, 0.0, 0.0)
    engine.node.create(3, 1.04, 0.0, 0.0)
    engine.node.create(4, 2.04, 0.0, 0.0)
    engine.node.create(5, 2.655, 0.0, 0.0)
    engine.node.create(6, 3.27, 0.0, 0.0)
    engine.node.create(7, 4.27, 0.0, 0.0)
    engine.node.create(8, 5.27, 0.0, 0.0)
    engine.node.create(9, 5.885, 0.0, 0.0)
    engine.node.create(10, 6.5, 0.0, 0.0)
    engine.node.create(11, 7.115, 0.0, 0.0)
    engine.node.create(12, 7.73, 0.0, 0.0)
    engine.node.create(13, 8.73, 0.0, 0.0)
    engine.node.create(14, 9.73, 0.0, 0.0)
    engine.node.create(15, 10.345, 0.0, 0.0)
    engine.node.create(16, 10.96, 0.0, 0.0)
    engine.node.create(17, 11.96, 0.0, 0.0)
    engine.node.create(18, 12.5, 0.0, 0.0)
    engine.node.create(19, 12.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
