"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.55, 0.0, 0.0)
    engine.node.create(3, 1.55, 0.0, 0.0)
    engine.node.create(4, 3.3, 0.0, 0.0)
    engine.node.create(5, 5.05, 0.0, 0.0)
    engine.node.create(6, 6.425, 0.0, 0.0)
    engine.node.create(7, 7.8, 0.0, 0.0)
    engine.node.create(8, 9.4, 0.0, 0.0)
    engine.node.create(9, 11.4, 0.0, 0.0)
    engine.node.create(10, 13.4, 0.0, 0.0)
    engine.node.create(11, 15.0, 0.0, 0.0)
    engine.node.create(12, 16.6, 0.0, 0.0)
    engine.node.create(13, 18.6, 0.0, 0.0)
    engine.node.create(14, 20.6, 0.0, 0.0)
    engine.node.create(15, 22.2, 0.0, 0.0)
    engine.node.create(16, 23.575, 0.0, 0.0)
    engine.node.create(17, 24.95, 0.0, 0.0)
    engine.node.create(18, 26.7, 0.0, 0.0)
    engine.node.create(19, 28.45, 0.0, 0.0)
    engine.node.create(20, 29.45, 0.0, 0.0)
    engine.node.create(21, 29.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
