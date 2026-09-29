"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.54, 0.0, 0.0)
    engine.node.create(3, 0.84, 0.0, 0.0)
    engine.node.create(4, 2.84, 0.0, 0.0)
    engine.node.create(5, 4.84, 0.0, 0.0)
    engine.node.create(6, 6.0, 0.0, 0.0)
    engine.node.create(7, 8.0, 0.0, 0.0)
    engine.node.create(8, 10.0, 0.0, 0.0)
    engine.node.create(9, 12.0, 0.0, 0.0)
    engine.node.create(10, 14.0, 0.0, 0.0)
    engine.node.create(11, 16.0, 0.0, 0.0)
    engine.node.create(12, 18.0, 0.0, 0.0)
    engine.node.create(13, 20.0, 0.0, 0.0)
    engine.node.create(14, 22.0, 0.0, 0.0)
    engine.node.create(15, 24.0, 0.0, 0.0)
    engine.node.create(16, 26.0, 0.0, 0.0)
    engine.node.create(17, 28.0, 0.0, 0.0)
    engine.node.create(18, 30.0, 0.0, 0.0)
    engine.node.create(19, 32.0, 0.0, 0.0)
    engine.node.create(20, 34.0, 0.0, 0.0)
    engine.node.create(21, 35.16, 0.0, 0.0)
    engine.node.create(22, 37.16, 0.0, 0.0)
    engine.node.create(23, 39.16, 0.0, 0.0)
    engine.node.create(24, 39.46, 0.0, 0.0)
    engine.node.create(25, 39.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
