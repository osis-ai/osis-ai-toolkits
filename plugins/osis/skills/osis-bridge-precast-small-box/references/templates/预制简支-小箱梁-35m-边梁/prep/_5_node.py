"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.54, 0.0, 0.0)
    engine.node.create(3, 0.84, 0.0, 0.0)
    engine.node.create(4, 2.59, 0.0, 0.0)
    engine.node.create(5, 4.34, 0.0, 0.0)
    engine.node.create(6, 5.5, 0.0, 0.0)
    engine.node.create(7, 7.5, 0.0, 0.0)
    engine.node.create(8, 9.5, 0.0, 0.0)
    engine.node.create(9, 11.5, 0.0, 0.0)
    engine.node.create(10, 13.5, 0.0, 0.0)
    engine.node.create(11, 15.5, 0.0, 0.0)
    engine.node.create(12, 17.5, 0.0, 0.0)
    engine.node.create(13, 19.5, 0.0, 0.0)
    engine.node.create(14, 21.5, 0.0, 0.0)
    engine.node.create(15, 23.5, 0.0, 0.0)
    engine.node.create(16, 25.5, 0.0, 0.0)
    engine.node.create(17, 27.5, 0.0, 0.0)
    engine.node.create(18, 29.5, 0.0, 0.0)
    engine.node.create(19, 30.66, 0.0, 0.0)
    engine.node.create(20, 32.41, 0.0, 0.0)
    engine.node.create(21, 34.16, 0.0, 0.0)
    engine.node.create(22, 34.46, 0.0, 0.0)
    engine.node.create(23, 34.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
