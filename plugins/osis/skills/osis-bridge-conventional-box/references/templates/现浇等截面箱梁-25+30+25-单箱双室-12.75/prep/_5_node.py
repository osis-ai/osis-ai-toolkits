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
    engine.node.create(10, 13.25, 0.0, 0.0)
    engine.node.create(11, 15.25, 0.0, 0.0)
    engine.node.create(12, 17.25, 0.0, 0.0)
    engine.node.create(13, 19.25, 0.0, 0.0)
    engine.node.create(14, 21.25, 0.0, 0.0)
    engine.node.create(15, 23.55, 0.0, 0.0)
    engine.node.create(16, 23.75, 0.0, 0.0)
    engine.node.create(17, 25.0, 0.0, 0.0)
    engine.node.create(18, 26.25, 0.0, 0.0)
    engine.node.create(19, 26.45, 0.0, 0.0)
    engine.node.create(20, 28.75, 0.0, 0.0)
    engine.node.create(21, 30.75, 0.0, 0.0)
    engine.node.create(22, 32.75, 0.0, 0.0)
    engine.node.create(23, 34.75, 0.0, 0.0)
    engine.node.create(24, 36.75, 0.0, 0.0)
    engine.node.create(25, 38.75, 0.0, 0.0)
    engine.node.create(26, 40.0, 0.0, 0.0)
    engine.node.create(27, 41.25, 0.0, 0.0)
    engine.node.create(28, 43.25, 0.0, 0.0)
    engine.node.create(29, 45.25, 0.0, 0.0)
    engine.node.create(30, 47.25, 0.0, 0.0)
    engine.node.create(31, 49.25, 0.0, 0.0)
    engine.node.create(32, 51.25, 0.0, 0.0)
    engine.node.create(33, 53.55, 0.0, 0.0)
    engine.node.create(34, 53.75, 0.0, 0.0)
    engine.node.create(35, 55.0, 0.0, 0.0)
    engine.node.create(36, 56.25, 0.0, 0.0)
    engine.node.create(37, 56.45, 0.0, 0.0)
    engine.node.create(38, 58.75, 0.0, 0.0)
    engine.node.create(39, 60.75, 0.0, 0.0)
    engine.node.create(40, 62.75, 0.0, 0.0)
    engine.node.create(41, 64.75, 0.0, 0.0)
    engine.node.create(42, 66.75, 0.0, 0.0)
    engine.node.create(43, 67.92, 0.0, 0.0)
    engine.node.create(44, 69.92, 0.0, 0.0)
    engine.node.create(45, 71.92, 0.0, 0.0)
    engine.node.create(46, 73.92, 0.0, 0.0)
    engine.node.create(47, 75.92, 0.0, 0.0)
    engine.node.create(48, 78.22, 0.0, 0.0)
    engine.node.create(49, 78.42, 0.0, 0.0)
    engine.node.create(50, 79.32, 0.0, 0.0)
    engine.node.create(51, 79.92, 0.0, 0.0)
    engine.node.create(100, 0.68, -3.375, -1.8)
    engine.node.create(101, 25.0, -3.375, -1.8)
    engine.node.create(102, 55.0, -3.375, -1.8)
    engine.node.create(103, 79.32, -3.375, -1.8)
    engine.node.create(104, 0.68, 3.375, -1.8)
    engine.node.create(105, 25.0, 3.375, -1.8)
    engine.node.create(106, 55.0, 3.375, -1.8)
    engine.node.create(107, 79.32, 3.375, -1.8)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
