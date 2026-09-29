"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.12, 0.0, 0.0)
    engine.node.create(2, 0.62, 0.0, 0.0)
    engine.node.create(3, 2.12, 0.0, 0.0)
    engine.node.create(4, 4.0, 0.0, 0.0)
    engine.node.create(5, 6.0, 0.0, 0.0)
    engine.node.create(6, 10.5, 0.0, 0.0)
    engine.node.create(7, 15.0, 0.0, 0.0)
    engine.node.create(8, 19.0, 0.0, 0.0)
    engine.node.create(9, 23.0, 0.0, 0.0)
    engine.node.create(10, 26.5, 0.0, 0.0)
    engine.node.create(11, 30.0, 0.0, 0.0)
    engine.node.create(12, 32.0, 0.0, 0.0)
    engine.node.create(13, 33.5, 0.0, 0.0)
    engine.node.create(14, 34.0, 0.0, 0.0)
    engine.node.create(15, 35.0, 0.0, 0.0)
    engine.node.create(16, 36.0, 0.0, 0.0)
    engine.node.create(17, 36.5, 0.0, 0.0)
    engine.node.create(18, 38.0, 0.0, 0.0)
    engine.node.create(19, 40.0, 0.0, 0.0)
    engine.node.create(20, 43.5, 0.0, 0.0)
    engine.node.create(21, 47.0, 0.0, 0.0)
    engine.node.create(22, 51.0, 0.0, 0.0)
    engine.node.create(23, 55.0, 0.0, 0.0)
    engine.node.create(24, 59.5, 0.0, 0.0)
    engine.node.create(25, 64.0, 0.0, 0.0)
    engine.node.create(26, 65.0, 0.0, 0.0)
    engine.node.create(27, 66.0, 0.0, 0.0)
    engine.node.create(28, 70.5, 0.0, 0.0)
    engine.node.create(29, 75.0, 0.0, 0.0)
    engine.node.create(30, 79.0, 0.0, 0.0)
    engine.node.create(31, 83.0, 0.0, 0.0)
    engine.node.create(32, 86.5, 0.0, 0.0)
    engine.node.create(33, 90.0, 0.0, 0.0)
    engine.node.create(34, 92.0, 0.0, 0.0)
    engine.node.create(35, 93.5, 0.0, 0.0)
    engine.node.create(36, 94.0, 0.0, 0.0)
    engine.node.create(37, 95.0, 0.0, 0.0)
    engine.node.create(38, 96.0, 0.0, 0.0)
    engine.node.create(39, 96.5, 0.0, 0.0)
    engine.node.create(40, 98.0, 0.0, 0.0)
    engine.node.create(41, 100.0, 0.0, 0.0)
    engine.node.create(42, 103.5, 0.0, 0.0)
    engine.node.create(43, 107.0, 0.0, 0.0)
    engine.node.create(44, 111.0, 0.0, 0.0)
    engine.node.create(45, 115.0, 0.0, 0.0)
    engine.node.create(46, 119.5, 0.0, 0.0)
    engine.node.create(47, 124.0, 0.0, 0.0)
    engine.node.create(48, 126.0, 0.0, 0.0)
    engine.node.create(49, 127.88, 0.0, 0.0)
    engine.node.create(50, 129.38, 0.0, 0.0)
    engine.node.create(51, 129.88, 0.0, 0.0)
    engine.node.create(52, 0.62, 2.8, -2.2)
    engine.node.create(53, 0.62, -2.8, -2.2)
    engine.node.create(54, 35.0, 2.8, -4.0)
    engine.node.create(55, 35.0, -2.8, -4.0)
    engine.node.create(56, 95.0, 2.8, -4.0)
    engine.node.create(57, 95.0, -2.8, -4.0)
    engine.node.create(58, 129.38, 2.8, -2.2)
    engine.node.create(59, 129.38, -2.8, -2.2)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
