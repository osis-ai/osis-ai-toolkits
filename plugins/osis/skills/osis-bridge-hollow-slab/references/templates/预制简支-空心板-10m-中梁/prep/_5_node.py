"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.03, 0.0, 0.0)
    engine.node.create(2, 0.43, 0.0, 0.0)
    engine.node.create(3, 0.68, 0.0, 0.0)
    engine.node.create(4, 1.68, 0.0, 0.0)
    engine.node.create(5, 2.34, 0.0, 0.0)
    engine.node.create(6, 3.0, 0.0, 0.0)
    engine.node.create(7, 4.0, 0.0, 0.0)
    engine.node.create(8, 5.0, 0.0, 0.0)
    engine.node.create(9, 6.0, 0.0, 0.0)
    engine.node.create(10, 7.0, 0.0, 0.0)
    engine.node.create(11, 7.66, 0.0, 0.0)
    engine.node.create(12, 8.32, 0.0, 0.0)
    engine.node.create(13, 9.32, 0.0, 0.0)
    engine.node.create(14, 9.57, 0.0, 0.0)
    engine.node.create(15, 9.97, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
