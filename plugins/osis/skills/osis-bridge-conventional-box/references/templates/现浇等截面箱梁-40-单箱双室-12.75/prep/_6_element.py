"""OSIS 命令流 ELEMENT 模块 — 单元(梁/弹簧)创建 + 分组"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_elements(engine: OSISEngine) -> None:
    # 创建单元（便捷入口，内部转发到对应 create_* 方法）
    engine.element.create(1, "BEAM3D", 1, 2, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(2, "BEAM3D", 2, 3, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(3, "BEAM3D", 3, 4, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(4, "BEAM3D", 4, 5, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(5, "BEAM3D", 5, 6, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(6, "BEAM3D", 6, 7, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(7, "BEAM3D", 7, 8, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(8, "BEAM3D", 8, 9, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(9, "BEAM3D", 9, 10, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(10, "BEAM3D", 10, 11, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(11, "BEAM3D", 11, 12, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(12, "BEAM3D", 12, 13, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(13, "BEAM3D", 13, 14, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(14, "BEAM3D", 14, 15, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(15, "BEAM3D", 15, 16, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(16, "BEAM3D", 16, 17, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(17, "BEAM3D", 17, 18, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(18, "BEAM3D", 18, 19, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(19, "BEAM3D", 19, 20, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(20, "BEAM3D", 20, 21, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(21, "BEAM3D", 21, 22, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(22, "BEAM3D", 22, 23, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(23, "BEAM3D", 23, 24, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(24, "BEAM3D", 24, 25, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(25, "BEAM3D", 25, 26, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(26, "BEAM3D", 26, 27, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(27, "BEAM3D", 27, 28, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(28, "BEAM3D", 28, 29, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(29, "BEAM3D", 29, 30, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(30, "BEAM3D", 30, 31, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(31, "BEAM3D", 31, 32, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(32, "BEAM3D", 32, 33, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(33, "BEAM3D", 33, 34, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(34, "BEAM3D", 34, 35, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(35, "BEAM3D", 35, 36, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(36, "BEAM3D", 36, 37, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(37, "BEAM3D", 37, 38, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(38, "BEAM3D", 38, 39, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(39, "BEAM3D", 39, 40, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(40, "BEAM3D", 40, 41, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(41, "BEAM3D", 41, 42, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    # 创建单元组
    engine.element.group.create("1_车道线单元组", "c")
    engine.element.group.create("1_车道线单元组", "a", "1to41")
    engine.element.group.create("2_车道线单元组", "c")
    engine.element.group.create("2_车道线单元组", "a", "1to41")
    engine.element.group.create("3_车道线单元组", "c")
    engine.element.group.create("3_车道线单元组", "a", "1to41")
    engine.element.group.create("B1单元组", "c")
    engine.element.group.create("B1单元组", "a", "1to41")
    engine.element.group.create("B2单元组", "c")
    engine.element.group.create("B2单元组", "a", "1to41")
    engine.element.group.create("B3单元组", "c")
    engine.element.group.create("B3单元组", "a", "1to41")
    engine.element.group.create("B4单元组", "c")
    engine.element.group.create("B4单元组", "a", "1to41")
    engine.element.group.create("全部", "c")
    engine.element.group.create("全部", "a", "1to41")
    engine.element.group.create("支座", "c")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_elements(engine)
