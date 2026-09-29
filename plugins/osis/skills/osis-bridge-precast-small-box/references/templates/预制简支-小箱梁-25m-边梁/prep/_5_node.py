"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.5, 0.0, 0.0)
    engine.node.create(3, 0.84, 0.0, 0.0)
    engine.node.create(4, 2.84, 0.0, 0.0)
    engine.node.create(5, 4.5, 0.0, 0.0)
    engine.node.create(6, 6.5, 0.0, 0.0)
    engine.node.create(7, 8.5, 0.0, 0.0)
    engine.node.create(8, 10.5, 0.0, 0.0)
    engine.node.create(9, 12.5, 0.0, 0.0)
    engine.node.create(10, 14.5, 0.0, 0.0)
    engine.node.create(11, 16.5, 0.0, 0.0)
    engine.node.create(12, 18.5, 0.0, 0.0)
    engine.node.create(13, 20.5, 0.0, 0.0)
    engine.node.create(14, 22.16, 0.0, 0.0)
    engine.node.create(15, 24.16, 0.0, 0.0)
    engine.node.create(16, 24.5, 0.0, 0.0)
    engine.node.create(17, 24.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
