"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.64, 0.0, 0.0)
    engine.node.create(3, 1.64, 0.0, 0.0)
    engine.node.create(4, 3.345, 0.0, 0.0)
    engine.node.create(5, 5.345, 0.0, 0.0)
    engine.node.create(6, 7.345, 0.0, 0.0)
    engine.node.create(7, 9.05, 0.0, 0.0)
    engine.node.create(8, 10.1625, 0.0, 0.0)
    engine.node.create(9, 11.275, 0.0, 0.0)
    engine.node.create(10, 13.275, 0.0, 0.0)
    engine.node.create(11, 15.275, 0.0, 0.0)
    engine.node.create(12, 16.3875, 0.0, 0.0)
    engine.node.create(13, 17.5, 0.0, 0.0)
    engine.node.create(14, 18.6125, 0.0, 0.0)
    engine.node.create(15, 19.725, 0.0, 0.0)
    engine.node.create(16, 21.725, 0.0, 0.0)
    engine.node.create(17, 23.725, 0.0, 0.0)
    engine.node.create(18, 24.8375, 0.0, 0.0)
    engine.node.create(19, 25.95, 0.0, 0.0)
    engine.node.create(20, 27.655, 0.0, 0.0)
    engine.node.create(21, 29.655, 0.0, 0.0)
    engine.node.create(22, 31.655, 0.0, 0.0)
    engine.node.create(23, 33.36, 0.0, 0.0)
    engine.node.create(24, 34.36, 0.0, 0.0)
    engine.node.create(25, 34.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
