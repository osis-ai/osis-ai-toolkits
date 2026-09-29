"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.08, 0.0, 0.0)
    engine.node.create(2, 0.5, 0.0, 0.0)
    engine.node.create(3, 0.58, 0.0, 0.0)
    engine.node.create(4, 1.5, 0.0, 0.0)
    engine.node.create(5, 2.85, 0.0, 0.0)
    engine.node.create(6, 4.2, 0.0, 0.0)
    engine.node.create(7, 5.39, 0.0, 0.0)
    engine.node.create(8, 6.58, 0.0, 0.0)
    engine.node.create(9, 8.2775, 0.0, 0.0)
    engine.node.create(10, 9.975, 0.0, 0.0)
    engine.node.create(11, 11.2775, 0.0, 0.0)
    engine.node.create(12, 12.58, 0.0, 0.0)
    engine.node.create(13, 14.165, 0.0, 0.0)
    engine.node.create(14, 15.75, 0.0, 0.0)
    engine.node.create(15, 17.1, 0.0, 0.0)
    engine.node.create(16, 18.45, 0.0, 0.0)
    engine.node.create(17, 18.58, 0.0, 0.0)
    engine.node.create(18, 19.45, 0.0, 0.0)
    engine.node.create(19, 19.7, 0.0, 0.0)
    engine.node.create(20, 20.0, 0.0, 0.0)
    engine.node.create(21, 20.3, 0.0, 0.0)
    engine.node.create(22, 20.55, 0.0, 0.0)
    engine.node.create(23, 21.55, 0.0, 0.0)
    engine.node.create(24, 22.9, 0.0, 0.0)
    engine.node.create(25, 24.25, 0.0, 0.0)
    engine.node.create(26, 25.375, 0.0, 0.0)
    engine.node.create(27, 26.5, 0.0, 0.0)
    engine.node.create(28, 28.25, 0.0, 0.0)
    engine.node.create(29, 30.0, 0.0, 0.0)
    engine.node.create(30, 31.25, 0.0, 0.0)
    engine.node.create(31, 32.5, 0.0, 0.0)
    engine.node.create(32, 34.125, 0.0, 0.0)
    engine.node.create(33, 35.75, 0.0, 0.0)
    engine.node.create(34, 37.1, 0.0, 0.0)
    engine.node.create(35, 38.45, 0.0, 0.0)
    engine.node.create(36, 39.45, 0.0, 0.0)
    engine.node.create(37, 39.7, 0.0, 0.0)
    engine.node.create(38, 40.0, 0.0, 0.0)
    engine.node.create(39, 40.3, 0.0, 0.0)
    engine.node.create(40, 40.55, 0.0, 0.0)
    engine.node.create(41, 41.42, 0.0, 0.0)
    engine.node.create(42, 41.55, 0.0, 0.0)
    engine.node.create(43, 42.9, 0.0, 0.0)
    engine.node.create(44, 44.25, 0.0, 0.0)
    engine.node.create(45, 45.835, 0.0, 0.0)
    engine.node.create(46, 47.42, 0.0, 0.0)
    engine.node.create(47, 48.7225, 0.0, 0.0)
    engine.node.create(48, 50.025, 0.0, 0.0)
    engine.node.create(49, 51.7225, 0.0, 0.0)
    engine.node.create(50, 53.42, 0.0, 0.0)
    engine.node.create(51, 54.61, 0.0, 0.0)
    engine.node.create(52, 55.8, 0.0, 0.0)
    engine.node.create(53, 57.15, 0.0, 0.0)
    engine.node.create(54, 58.5, 0.0, 0.0)
    engine.node.create(55, 59.42, 0.0, 0.0)
    engine.node.create(56, 59.5, 0.0, 0.0)
    engine.node.create(57, 59.92, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
