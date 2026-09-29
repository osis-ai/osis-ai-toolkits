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
    engine.node.create(5, 3.02, 0.0, 0.0)
    engine.node.create(6, 4.02, 0.0, 0.0)
    engine.node.create(7, 5.02, 0.0, 0.0)
    engine.node.create(8, 6.02, 0.0, 0.0)
    engine.node.create(9, 7.02, 0.0, 0.0)
    engine.node.create(10, 8.0, 0.0, 0.0)
    engine.node.create(11, 8.98, 0.0, 0.0)
    engine.node.create(12, 9.98, 0.0, 0.0)
    engine.node.create(13, 10.98, 0.0, 0.0)
    engine.node.create(14, 11.98, 0.0, 0.0)
    engine.node.create(15, 12.98, 0.0, 0.0)
    engine.node.create(16, 13.96, 0.0, 0.0)
    engine.node.create(17, 14.96, 0.0, 0.0)
    engine.node.create(18, 15.5, 0.0, 0.0)
    engine.node.create(19, 15.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
