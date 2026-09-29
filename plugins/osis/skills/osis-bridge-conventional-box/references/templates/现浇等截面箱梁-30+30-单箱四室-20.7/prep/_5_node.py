"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.08, 0.0, 0.0)
    engine.node.create(2, 0.68, 0.0, 0.0)
    engine.node.create(3, 1.58, 0.0, 0.0)
    engine.node.create(4, 1.78, 0.0, 0.0)
    engine.node.create(5, 4.08, 0.0, 0.0)
    engine.node.create(6, 6.08, 0.0, 0.0)
    engine.node.create(7, 8.08, 0.0, 0.0)
    engine.node.create(8, 10.08, 0.0, 0.0)
    engine.node.create(9, 12.08, 0.0, 0.0)
    engine.node.create(10, 14.08, 0.0, 0.0)
    engine.node.create(11, 16.25, 0.0, 0.0)
    engine.node.create(12, 18.25, 0.0, 0.0)
    engine.node.create(13, 20.25, 0.0, 0.0)
    engine.node.create(14, 22.25, 0.0, 0.0)
    engine.node.create(15, 24.25, 0.0, 0.0)
    engine.node.create(16, 26.25, 0.0, 0.0)
    engine.node.create(17, 28.55, 0.0, 0.0)
    engine.node.create(18, 28.75, 0.0, 0.0)
    engine.node.create(19, 30.0, 0.0, 0.0)
    engine.node.create(20, 31.25, 0.0, 0.0)
    engine.node.create(21, 31.45, 0.0, 0.0)
    engine.node.create(22, 33.75, 0.0, 0.0)
    engine.node.create(23, 35.75, 0.0, 0.0)
    engine.node.create(24, 37.75, 0.0, 0.0)
    engine.node.create(25, 39.75, 0.0, 0.0)
    engine.node.create(26, 41.75, 0.0, 0.0)
    engine.node.create(27, 43.75, 0.0, 0.0)
    engine.node.create(28, 45.92, 0.0, 0.0)
    engine.node.create(29, 47.92, 0.0, 0.0)
    engine.node.create(30, 49.92, 0.0, 0.0)
    engine.node.create(31, 51.92, 0.0, 0.0)
    engine.node.create(32, 53.92, 0.0, 0.0)
    engine.node.create(33, 55.92, 0.0, 0.0)
    engine.node.create(34, 58.22, 0.0, 0.0)
    engine.node.create(35, 58.42, 0.0, 0.0)
    engine.node.create(36, 59.32, 0.0, 0.0)
    engine.node.create(37, 59.92, 0.0, 0.0)
    engine.node.create(100, 0.68, -7.35, -1.8)
    engine.node.create(101, 30.0, -7.35, -1.8)
    engine.node.create(102, 59.32, -7.35, -1.8)
    engine.node.create(103, 0.68, 0.0, -1.8)
    engine.node.create(104, 30.0, 0.0, -1.8)
    engine.node.create(105, 59.32, 0.0, -1.8)
    engine.node.create(106, 0.68, 7.35, -1.8)
    engine.node.create(107, 30.0, 7.35, -1.8)
    engine.node.create(108, 59.32, 7.35, -1.8)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
