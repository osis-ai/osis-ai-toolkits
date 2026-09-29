"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.54, 0.0, 0.0)
    engine.node.create(3, 1.54, 0.0, 0.0)
    engine.node.create(4, 2.5175, 0.0, 0.0)
    engine.node.create(5, 3.495, 0.0, 0.0)
    engine.node.create(6, 4.4725, 0.0, 0.0)
    engine.node.create(7, 5.45, 0.0, 0.0)
    engine.node.create(8, 6.4275, 0.0, 0.0)
    engine.node.create(9, 7.405, 0.0, 0.0)
    engine.node.create(10, 8.3825, 0.0, 0.0)
    engine.node.create(11, 9.36, 0.0, 0.0)
    engine.node.create(12, 10.3375, 0.0, 0.0)
    engine.node.create(13, 11.315, 0.0, 0.0)
    engine.node.create(14, 12.2925, 0.0, 0.0)
    engine.node.create(15, 13.27, 0.0, 0.0)
    engine.node.create(16, 14.2475, 0.0, 0.0)
    engine.node.create(17, 15.225, 0.0, 0.0)
    engine.node.create(18, 16.2025, 0.0, 0.0)
    engine.node.create(19, 17.18, 0.0, 0.0)
    engine.node.create(20, 18.1575, 0.0, 0.0)
    engine.node.create(21, 19.135, 0.0, 0.0)
    engine.node.create(22, 20.1125, 0.0, 0.0)
    engine.node.create(23, 21.09, 0.0, 0.0)
    engine.node.create(24, 22.0675, 0.0, 0.0)
    engine.node.create(25, 23.045, 0.0, 0.0)
    engine.node.create(26, 23.75, 0.0, 0.0)
    engine.node.create(27, 25.0, 0.0, 0.0)
    engine.node.create(28, 26.25, 0.0, 0.0)
    engine.node.create(29, 27.0417, 0.0, 0.0)
    engine.node.create(30, 28.0625, 0.0, 0.0)
    engine.node.create(31, 29.0833, 0.0, 0.0)
    engine.node.create(32, 30.1042, 0.0, 0.0)
    engine.node.create(33, 31.125, 0.0, 0.0)
    engine.node.create(34, 32.1458, 0.0, 0.0)
    engine.node.create(35, 33.1667, 0.0, 0.0)
    engine.node.create(36, 34.1875, 0.0, 0.0)
    engine.node.create(37, 35.2083, 0.0, 0.0)
    engine.node.create(38, 36.2292, 0.0, 0.0)
    engine.node.create(39, 37.25, 0.0, 0.0)
    engine.node.create(40, 38.2708, 0.0, 0.0)
    engine.node.create(41, 39.2917, 0.0, 0.0)
    engine.node.create(42, 40.3125, 0.0, 0.0)
    engine.node.create(43, 41.3333, 0.0, 0.0)
    engine.node.create(44, 42.3542, 0.0, 0.0)
    engine.node.create(45, 43.375, 0.0, 0.0)
    engine.node.create(46, 44.3958, 0.0, 0.0)
    engine.node.create(47, 45.4167, 0.0, 0.0)
    engine.node.create(48, 46.4375, 0.0, 0.0)
    engine.node.create(49, 47.4583, 0.0, 0.0)
    engine.node.create(50, 48.0, 0.0, 0.0)
    engine.node.create(51, 48.46, 0.0, 0.0)
    engine.node.create(52, 49.46, 0.0, 0.0)
    engine.node.create(53, 49.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
