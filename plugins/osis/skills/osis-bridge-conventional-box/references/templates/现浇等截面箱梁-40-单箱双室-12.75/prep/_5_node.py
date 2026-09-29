"""OSIS 命令流 NODE 模块 — 节点坐标"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_nodes(engine: OSISEngine) -> None:
    # 创建节点
    engine.node.create(1, 0.04, 0.0, 0.0)
    engine.node.create(2, 0.54, 0.0, 0.0)
    engine.node.create(3, 1.54, 0.0, 0.0)
    engine.node.create(4, 2.5378, 0.0, 0.0)
    engine.node.create(5, 3.5357, 0.0, 0.0)
    engine.node.create(6, 4.5335, 0.0, 0.0)
    engine.node.create(7, 5.5314, 0.0, 0.0)
    engine.node.create(8, 6.5292, 0.0, 0.0)
    engine.node.create(9, 7.527, 0.0, 0.0)
    engine.node.create(10, 8.5249, 0.0, 0.0)
    engine.node.create(11, 9.5227, 0.0, 0.0)
    engine.node.create(12, 10.5205, 0.0, 0.0)
    engine.node.create(13, 11.5184, 0.0, 0.0)
    engine.node.create(14, 12.5162, 0.0, 0.0)
    engine.node.create(15, 13.5141, 0.0, 0.0)
    engine.node.create(16, 14.5119, 0.0, 0.0)
    engine.node.create(17, 15.5097, 0.0, 0.0)
    engine.node.create(18, 16.5076, 0.0, 0.0)
    engine.node.create(19, 17.5054, 0.0, 0.0)
    engine.node.create(20, 18.5032, 0.0, 0.0)
    engine.node.create(21, 19.5011, 0.0, 0.0)
    engine.node.create(22, 20.4989, 0.0, 0.0)
    engine.node.create(23, 21.4968, 0.0, 0.0)
    engine.node.create(24, 22.4946, 0.0, 0.0)
    engine.node.create(25, 23.4924, 0.0, 0.0)
    engine.node.create(26, 24.4903, 0.0, 0.0)
    engine.node.create(27, 25.4881, 0.0, 0.0)
    engine.node.create(28, 26.4859, 0.0, 0.0)
    engine.node.create(29, 27.4838, 0.0, 0.0)
    engine.node.create(30, 28.4816, 0.0, 0.0)
    engine.node.create(31, 29.4795, 0.0, 0.0)
    engine.node.create(32, 30.4773, 0.0, 0.0)
    engine.node.create(33, 31.4751, 0.0, 0.0)
    engine.node.create(34, 32.473, 0.0, 0.0)
    engine.node.create(35, 33.4708, 0.0, 0.0)
    engine.node.create(36, 34.4686, 0.0, 0.0)
    engine.node.create(37, 35.4665, 0.0, 0.0)
    engine.node.create(38, 36.4643, 0.0, 0.0)
    engine.node.create(39, 37.4622, 0.0, 0.0)
    engine.node.create(40, 38.46, 0.0, 0.0)
    engine.node.create(41, 39.46, 0.0, 0.0)
    engine.node.create(42, 39.96, 0.0, 0.0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_nodes(engine)
