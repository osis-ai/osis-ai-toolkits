"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.64, 0.0, 0.0)
    engine.node.create(3, 1.64, 0.0, 0.0)
    engine.node.create(4, 2.805, 0.0, 0.0)
    engine.node.create(5, 3.97, 0.0, 0.0)
    engine.node.create(6, 5.97, 0.0, 0.0)
    engine.node.create(7, 7.97, 0.0, 0.0)
    engine.node.create(8, 9.135, 0.0, 0.0)
    engine.node.create(9, 10.3, 0.0, 0.0)
    engine.node.create(10, 11.15, 0.0, 0.0)
    engine.node.create(11, 13.15, 0.0, 0.0)
    engine.node.create(12, 15.15, 0.0, 0.0)
    engine.node.create(13, 17.15, 0.0, 0.0)
    engine.node.create(14, 19.15, 0.0, 0.0)
    engine.node.create(15, 20.0, 0.0, 0.0)
    engine.node.create(16, 20.85, 0.0, 0.0)
    engine.node.create(17, 22.85, 0.0, 0.0)
    engine.node.create(18, 24.85, 0.0, 0.0)
    engine.node.create(19, 26.85, 0.0, 0.0)
    engine.node.create(20, 28.85, 0.0, 0.0)
    engine.node.create(21, 29.7, 0.0, 0.0)
    engine.node.create(22, 30.865, 0.0, 0.0)
    engine.node.create(23, 32.03, 0.0, 0.0)
    engine.node.create(24, 34.03, 0.0, 0.0)
    engine.node.create(25, 36.03, 0.0, 0.0)
    engine.node.create(26, 37.195, 0.0, 0.0)
    engine.node.create(27, 38.36, 0.0, 0.0)
    engine.node.create(28, 39.36, 0.0, 0.0)
    engine.node.create(29, 39.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
