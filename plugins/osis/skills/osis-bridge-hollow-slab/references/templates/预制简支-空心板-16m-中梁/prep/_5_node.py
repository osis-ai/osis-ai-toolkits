"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.03, 0.0, 0.0)
    engine.node.create(2, 0.46, 0.0, 0.0)
    engine.node.create(3, 0.68, 0.0, 0.0)
    engine.node.create(4, 1.68, 0.0, 0.0)
    engine.node.create(5, 2.84, 0.0, 0.0)
    engine.node.create(6, 4.0, 0.0, 0.0)
    engine.node.create(7, 6.0, 0.0, 0.0)
    engine.node.create(8, 8.0, 0.0, 0.0)
    engine.node.create(9, 10.0, 0.0, 0.0)
    engine.node.create(10, 12.0, 0.0, 0.0)
    engine.node.create(11, 13.16, 0.0, 0.0)
    engine.node.create(12, 14.32, 0.0, 0.0)
    engine.node.create(13, 15.32, 0.0, 0.0)
    engine.node.create(14, 15.54, 0.0, 0.0)
    engine.node.create(15, 15.97, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
