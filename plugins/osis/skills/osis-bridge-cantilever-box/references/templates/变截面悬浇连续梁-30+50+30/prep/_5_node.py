"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.12, 0.0, 0.0)
    engine.node.create(2, 0.62, 0.0, 0.0)
    engine.node.create(3, 2.12, 0.0, 0.0)
    engine.node.create(4, 2.72, 0.0, 0.0)
    engine.node.create(5, 4.0, 0.0, 0.0)
    engine.node.create(6, 6.0, 0.0, 0.0)
    engine.node.create(7, 10.0, 0.0, 0.0)
    engine.node.create(8, 14.0, 0.0, 0.0)
    engine.node.create(9, 17.5, 0.0, 0.0)
    engine.node.create(10, 21.0, 0.0, 0.0)
    engine.node.create(11, 24.5, 0.0, 0.0)
    engine.node.create(12, 27.5, 0.0, 0.0)
    engine.node.create(13, 28.5, 0.0, 0.0)
    engine.node.create(14, 29.0, 0.0, 0.0)
    engine.node.create(15, 30.0, 0.0, 0.0)
    engine.node.create(16, 31.0, 0.0, 0.0)
    engine.node.create(17, 31.5, 0.0, 0.0)
    engine.node.create(18, 32.5, 0.0, 0.0)
    engine.node.create(19, 35.5, 0.0, 0.0)
    engine.node.create(20, 39.0, 0.0, 0.0)
    engine.node.create(21, 42.5, 0.0, 0.0)
    engine.node.create(22, 46.0, 0.0, 0.0)
    engine.node.create(23, 50.0, 0.0, 0.0)
    engine.node.create(24, 54.0, 0.0, 0.0)
    engine.node.create(25, 55.0, 0.0, 0.0)
    engine.node.create(26, 56.0, 0.0, 0.0)
    engine.node.create(27, 60.0, 0.0, 0.0)
    engine.node.create(28, 64.0, 0.0, 0.0)
    engine.node.create(29, 67.5, 0.0, 0.0)
    engine.node.create(30, 71.0, 0.0, 0.0)
    engine.node.create(31, 74.5, 0.0, 0.0)
    engine.node.create(32, 77.5, 0.0, 0.0)
    engine.node.create(33, 78.5, 0.0, 0.0)
    engine.node.create(34, 79.0, 0.0, 0.0)
    engine.node.create(35, 80.0, 0.0, 0.0)
    engine.node.create(36, 81.0, 0.0, 0.0)
    engine.node.create(37, 81.5, 0.0, 0.0)
    engine.node.create(38, 82.5, 0.0, 0.0)
    engine.node.create(39, 85.5, 0.0, 0.0)
    engine.node.create(40, 89.0, 0.0, 0.0)
    engine.node.create(41, 92.5, 0.0, 0.0)
    engine.node.create(42, 96.0, 0.0, 0.0)
    engine.node.create(43, 100.0, 0.0, 0.0)
    engine.node.create(44, 104.0, 0.0, 0.0)
    engine.node.create(45, 106.0, 0.0, 0.0)
    engine.node.create(46, 107.28, 0.0, 0.0)
    engine.node.create(47, 107.88, 0.0, 0.0)
    engine.node.create(48, 109.38, 0.0, 0.0)
    engine.node.create(49, 109.88, 0.0, 0.0)
    engine.node.create(50, 0.62, 2.8, -2.2)
    engine.node.create(51, 0.62, -2.8, -2.2)
    engine.node.create(52, 30.0, 2.8, -3.2)
    engine.node.create(53, 30.0, -2.8, -3.2)
    engine.node.create(54, 80.0, 2.8, -3.2)
    engine.node.create(55, 80.0, -2.8, -3.2)
    engine.node.create(56, 109.38, 2.8, -2.2)
    engine.node.create(57, 109.38, -2.8, -2.2)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
