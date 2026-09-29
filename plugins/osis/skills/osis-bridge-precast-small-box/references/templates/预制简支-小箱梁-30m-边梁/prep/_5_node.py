"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.58, 0.0, 0.0)
    engine.node.create(3, 0.84, 0.0, 0.0)
    engine.node.create(4, 2.84, 0.0, 0.0)
    engine.node.create(5, 3.92, 0.0, 0.0)
    engine.node.create(6, 5.0, 0.0, 0.0)
    engine.node.create(7, 7.0, 0.0, 0.0)
    engine.node.create(8, 9.0, 0.0, 0.0)
    engine.node.create(9, 11.0, 0.0, 0.0)
    engine.node.create(10, 13.0, 0.0, 0.0)
    engine.node.create(11, 15.0, 0.0, 0.0)
    engine.node.create(12, 17.0, 0.0, 0.0)
    engine.node.create(13, 19.0, 0.0, 0.0)
    engine.node.create(14, 21.0, 0.0, 0.0)
    engine.node.create(15, 23.0, 0.0, 0.0)
    engine.node.create(16, 25.0, 0.0, 0.0)
    engine.node.create(17, 26.08, 0.0, 0.0)
    engine.node.create(18, 27.16, 0.0, 0.0)
    engine.node.create(19, 29.16, 0.0, 0.0)
    engine.node.create(20, 29.42, 0.0, 0.0)
    engine.node.create(21, 29.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
