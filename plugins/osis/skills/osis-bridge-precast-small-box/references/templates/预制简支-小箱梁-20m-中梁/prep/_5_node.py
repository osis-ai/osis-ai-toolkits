"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.45, 0.0, 0.0)
    engine.node.create(3, 0.84, 0.0, 0.0)
    engine.node.create(4, 2.84, 0.0, 0.0)
    engine.node.create(5, 4.0, 0.0, 0.0)
    engine.node.create(6, 6.0, 0.0, 0.0)
    engine.node.create(7, 8.0, 0.0, 0.0)
    engine.node.create(8, 10.0, 0.0, 0.0)
    engine.node.create(9, 12.0, 0.0, 0.0)
    engine.node.create(10, 14.0, 0.0, 0.0)
    engine.node.create(11, 16.0, 0.0, 0.0)
    engine.node.create(12, 17.16, 0.0, 0.0)
    engine.node.create(13, 19.16, 0.0, 0.0)
    engine.node.create(14, 19.55, 0.0, 0.0)
    engine.node.create(15, 19.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
