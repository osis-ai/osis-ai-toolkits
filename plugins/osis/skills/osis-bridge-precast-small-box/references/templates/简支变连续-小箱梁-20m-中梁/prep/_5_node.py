"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.49, 0.0, 0.0)
    engine.node.create(3, 0.84, 0.0, 0.0)
    engine.node.create(4, 2.84, 0.0, 0.0)
    engine.node.create(5, 4.4612, 0.0, 0.0)
    engine.node.create(6, 6.4612, 0.0, 0.0)
    engine.node.create(7, 8.4612, 0.0, 0.0)
    engine.node.create(8, 10.0825, 0.0, 0.0)
    engine.node.create(9, 11.7037, 0.0, 0.0)
    engine.node.create(10, 13.7037, 0.0, 0.0)
    engine.node.create(11, 15.7037, 0.0, 0.0)
    engine.node.create(12, 17.325, 0.0, 0.0)
    engine.node.create(13, 19.325, 0.0, 0.0)
    engine.node.create(14, 19.5, 0.0, 0.0)
    engine.node.create(15, 19.825, 0.0, 0.0)
    engine.node.create(16, 20.0, 0.0, 0.0)
    engine.node.create(17, 20.175, 0.0, 0.0)
    engine.node.create(18, 20.5, 0.0, 0.0)
    engine.node.create(19, 20.675, 0.0, 0.0)
    engine.node.create(20, 22.675, 0.0, 0.0)
    engine.node.create(21, 24.3375, 0.0, 0.0)
    engine.node.create(22, 26.3375, 0.0, 0.0)
    engine.node.create(23, 28.3375, 0.0, 0.0)
    engine.node.create(24, 30.0, 0.0, 0.0)
    engine.node.create(25, 31.6625, 0.0, 0.0)
    engine.node.create(26, 33.6625, 0.0, 0.0)
    engine.node.create(27, 35.6625, 0.0, 0.0)
    engine.node.create(28, 37.325, 0.0, 0.0)
    engine.node.create(29, 39.325, 0.0, 0.0)
    engine.node.create(30, 39.5, 0.0, 0.0)
    engine.node.create(31, 39.825, 0.0, 0.0)
    engine.node.create(32, 40.0, 0.0, 0.0)
    engine.node.create(33, 40.175, 0.0, 0.0)
    engine.node.create(34, 40.5, 0.0, 0.0)
    engine.node.create(35, 40.675, 0.0, 0.0)
    engine.node.create(36, 42.675, 0.0, 0.0)
    engine.node.create(37, 44.2962, 0.0, 0.0)
    engine.node.create(38, 46.2962, 0.0, 0.0)
    engine.node.create(39, 48.2962, 0.0, 0.0)
    engine.node.create(40, 49.9175, 0.0, 0.0)
    engine.node.create(41, 51.5387, 0.0, 0.0)
    engine.node.create(42, 53.5387, 0.0, 0.0)
    engine.node.create(43, 55.5387, 0.0, 0.0)
    engine.node.create(44, 57.16, 0.0, 0.0)
    engine.node.create(45, 59.16, 0.0, 0.0)
    engine.node.create(46, 59.51, 0.0, 0.0)
    engine.node.create(47, 59.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
