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
    engine.node.create(5, 3.7113, 0.0, 0.0)
    engine.node.create(6, 5.7112, 0.0, 0.0)
    engine.node.create(7, 7.7112, 0.0, 0.0)
    engine.node.create(8, 9.7112, 0.0, 0.0)
    engine.node.create(9, 11.7112, 0.0, 0.0)
    engine.node.create(10, 12.5825, 0.0, 0.0)
    engine.node.create(11, 13.4537, 0.0, 0.0)
    engine.node.create(12, 15.4537, 0.0, 0.0)
    engine.node.create(13, 17.4537, 0.0, 0.0)
    engine.node.create(14, 19.4537, 0.0, 0.0)
    engine.node.create(15, 21.4537, 0.0, 0.0)
    engine.node.create(16, 22.325, 0.0, 0.0)
    engine.node.create(17, 24.325, 0.0, 0.0)
    engine.node.create(18, 24.5, 0.0, 0.0)
    engine.node.create(19, 24.825, 0.0, 0.0)
    engine.node.create(20, 25.0, 0.0, 0.0)
    engine.node.create(21, 25.175, 0.0, 0.0)
    engine.node.create(22, 25.5, 0.0, 0.0)
    engine.node.create(23, 25.675, 0.0, 0.0)
    engine.node.create(24, 27.675, 0.0, 0.0)
    engine.node.create(25, 28.5875, 0.0, 0.0)
    engine.node.create(26, 30.5875, 0.0, 0.0)
    engine.node.create(27, 32.5875, 0.0, 0.0)
    engine.node.create(28, 34.5875, 0.0, 0.0)
    engine.node.create(29, 36.5875, 0.0, 0.0)
    engine.node.create(30, 37.5, 0.0, 0.0)
    engine.node.create(31, 38.4125, 0.0, 0.0)
    engine.node.create(32, 40.4125, 0.0, 0.0)
    engine.node.create(33, 42.4125, 0.0, 0.0)
    engine.node.create(34, 44.4125, 0.0, 0.0)
    engine.node.create(35, 46.4125, 0.0, 0.0)
    engine.node.create(36, 47.325, 0.0, 0.0)
    engine.node.create(37, 49.325, 0.0, 0.0)
    engine.node.create(38, 49.5, 0.0, 0.0)
    engine.node.create(39, 49.825, 0.0, 0.0)
    engine.node.create(40, 50.0, 0.0, 0.0)
    engine.node.create(41, 50.175, 0.0, 0.0)
    engine.node.create(42, 50.5, 0.0, 0.0)
    engine.node.create(43, 50.675, 0.0, 0.0)
    engine.node.create(44, 52.675, 0.0, 0.0)
    engine.node.create(45, 53.5463, 0.0, 0.0)
    engine.node.create(46, 55.5463, 0.0, 0.0)
    engine.node.create(47, 57.5463, 0.0, 0.0)
    engine.node.create(48, 59.5463, 0.0, 0.0)
    engine.node.create(49, 61.5463, 0.0, 0.0)
    engine.node.create(50, 62.4175, 0.0, 0.0)
    engine.node.create(51, 63.2888, 0.0, 0.0)
    engine.node.create(52, 65.2887, 0.0, 0.0)
    engine.node.create(53, 67.2887, 0.0, 0.0)
    engine.node.create(54, 69.2887, 0.0, 0.0)
    engine.node.create(55, 71.2887, 0.0, 0.0)
    engine.node.create(56, 72.16, 0.0, 0.0)
    engine.node.create(57, 74.16, 0.0, 0.0)
    engine.node.create(58, 74.46, 0.0, 0.0)
    engine.node.create(59, 74.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
