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
    engine.node.create(8, 9.165, 0.0, 0.0)
    engine.node.create(9, 11.165, 0.0, 0.0)
    engine.node.create(10, 12.25, 0.0, 0.0)
    engine.node.create(11, 14.25, 0.0, 0.0)
    engine.node.create(12, 16.25, 0.0, 0.0)
    engine.node.create(13, 18.55, 0.0, 0.0)
    engine.node.create(14, 18.75, 0.0, 0.0)
    engine.node.create(15, 20.0, 0.0, 0.0)
    engine.node.create(16, 21.25, 0.0, 0.0)
    engine.node.create(17, 21.45, 0.0, 0.0)
    engine.node.create(18, 23.75, 0.0, 0.0)
    engine.node.create(19, 25.75, 0.0, 0.0)
    engine.node.create(20, 27.75, 0.0, 0.0)
    engine.node.create(21, 29.75, 0.0, 0.0)
    engine.node.create(22, 31.75, 0.0, 0.0)
    engine.node.create(23, 33.75, 0.0, 0.0)
    engine.node.create(24, 35.0, 0.0, 0.0)
    engine.node.create(25, 36.25, 0.0, 0.0)
    engine.node.create(26, 38.25, 0.0, 0.0)
    engine.node.create(27, 40.25, 0.0, 0.0)
    engine.node.create(28, 42.25, 0.0, 0.0)
    engine.node.create(29, 44.25, 0.0, 0.0)
    engine.node.create(30, 46.25, 0.0, 0.0)
    engine.node.create(31, 48.55, 0.0, 0.0)
    engine.node.create(32, 48.75, 0.0, 0.0)
    engine.node.create(33, 50.0, 0.0, 0.0)
    engine.node.create(34, 51.25, 0.0, 0.0)
    engine.node.create(35, 51.45, 0.0, 0.0)
    engine.node.create(36, 53.75, 0.0, 0.0)
    engine.node.create(37, 55.75, 0.0, 0.0)
    engine.node.create(38, 57.75, 0.0, 0.0)
    engine.node.create(39, 58.835, 0.0, 0.0)
    engine.node.create(40, 60.835, 0.0, 0.0)
    engine.node.create(41, 61.92, 0.0, 0.0)
    engine.node.create(42, 63.92, 0.0, 0.0)
    engine.node.create(43, 65.92, 0.0, 0.0)
    engine.node.create(44, 68.22, 0.0, 0.0)
    engine.node.create(45, 68.42, 0.0, 0.0)
    engine.node.create(46, 69.32, 0.0, 0.0)
    engine.node.create(47, 69.92, 0.0, 0.0)
    engine.node.create(100, 0.68, -3.375, -1.8)
    engine.node.create(101, 20.0, -3.375, -1.8)
    engine.node.create(102, 50.0, -3.375, -1.8)
    engine.node.create(103, 69.32, -3.375, -1.8)
    engine.node.create(104, 0.68, 3.375, -1.8)
    engine.node.create(105, 20.0, 3.375, -1.8)
    engine.node.create(106, 50.0, 3.375, -1.8)
    engine.node.create(107, 69.32, 3.375, -1.8)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
