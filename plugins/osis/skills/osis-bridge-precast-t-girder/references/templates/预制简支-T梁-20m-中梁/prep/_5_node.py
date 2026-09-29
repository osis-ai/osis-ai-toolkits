"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.5, 0.0, 0.0)
    engine.node.create(3, 1.5, 0.0, 0.0)
    engine.node.create(4, 2.75, 0.0, 0.0)
    engine.node.create(5, 4.0, 0.0, 0.0)
    engine.node.create(6, 5.0, 0.0, 0.0)
    engine.node.create(7, 7.0, 0.0, 0.0)
    engine.node.create(8, 9.0, 0.0, 0.0)
    engine.node.create(9, 10.0, 0.0, 0.0)
    engine.node.create(10, 11.0, 0.0, 0.0)
    engine.node.create(11, 13.0, 0.0, 0.0)
    engine.node.create(12, 15.0, 0.0, 0.0)
    engine.node.create(13, 16.0, 0.0, 0.0)
    engine.node.create(14, 17.25, 0.0, 0.0)
    engine.node.create(15, 18.5, 0.0, 0.0)
    engine.node.create(16, 19.5, 0.0, 0.0)
    engine.node.create(17, 19.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
