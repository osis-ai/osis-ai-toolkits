"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.5, 0.0, 0.0)
    engine.node.create(3, 1.5, 0.0, 0.0)
    engine.node.create(4, 2.85, 0.0, 0.0)
    engine.node.create(5, 4.2, 0.0, 0.0)
    engine.node.create(6, 5.85, 0.0, 0.0)
    engine.node.create(7, 7.85, 0.0, 0.0)
    engine.node.create(8, 9.85, 0.0, 0.0)
    engine.node.create(9, 11.5, 0.0, 0.0)
    engine.node.create(10, 12.5, 0.0, 0.0)
    engine.node.create(11, 13.575, 0.0, 0.0)
    engine.node.create(12, 14.65, 0.0, 0.0)
    engine.node.create(13, 16.65, 0.0, 0.0)
    engine.node.create(14, 18.65, 0.0, 0.0)
    engine.node.create(15, 19.725, 0.0, 0.0)
    engine.node.create(16, 20.8, 0.0, 0.0)
    engine.node.create(17, 22.5, 0.0, 0.0)
    engine.node.create(18, 23.5, 0.0, 0.0)
    engine.node.create(19, 24.5, 0.0, 0.0)
    engine.node.create(20, 24.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
