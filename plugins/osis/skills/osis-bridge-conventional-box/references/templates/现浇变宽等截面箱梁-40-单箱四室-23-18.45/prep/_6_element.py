"""OSIS 命令流 ELEMENT 模块 — 单元(梁/弹簧)创建 + 分组"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_elements(engine: OSISEngine) -> None:
    # 创建单元（便捷入口，内部转发到对应 create_* 方法）
    engine.element.create(1, "BEAM3D", 1, 2, 1, 50001, 50002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(2, "BEAM3D", 2, 3, 1, 60001, 60002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(3, "BEAM3D", 3, 4, 1, 70001, 70002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(4, "BEAM3D", 4, 5, 1, 80001, 80002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(5, "BEAM3D", 5, 6, 1, 90001, 90002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(6, "BEAM3D", 6, 7, 1, 100001, 100002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(7, "BEAM3D", 7, 8, 1, 110001, 110002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(8, "BEAM3D", 8, 9, 1, 120001, 120002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(9, "BEAM3D", 9, 10, 1, 130001, 130002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(10, "BEAM3D", 10, 11, 1, 140001, 140002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(11, "BEAM3D", 11, 12, 1, 150001, 150002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(12, "BEAM3D", 12, 13, 1, 160001, 160002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(13, "BEAM3D", 13, 14, 1, 170001, 170002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(14, "BEAM3D", 14, 15, 1, 180001, 180002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(15, "BEAM3D", 15, 16, 1, 190001, 190002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(16, "BEAM3D", 16, 17, 1, 200001, 200002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(17, "BEAM3D", 17, 18, 1, 210001, 210002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(18, "BEAM3D", 18, 19, 1, 220001, 220002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(19, "BEAM3D", 19, 20, 1, 230001, 230002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(20, "BEAM3D", 20, 21, 1, 240001, 240002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(21, "BEAM3D", 21, 22, 1, 250001, 250002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(22, "BEAM3D", 22, 23, 1, 260001, 260002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(23, "BEAM3D", 23, 24, 1, 270001, 270002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(24, "BEAM3D", 24, 25, 1, 280001, 280002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(25, "BEAM3D", 25, 26, 1, 290001, 290002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(26, "BEAM3D", 26, 27, 1, 300001, 300002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(27, "BEAM3D", 27, 28, 1, 310001, 310002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(28, "BEAM3D", 28, 29, 1, 320001, 320002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(29, "BEAM3D", 29, 30, 1, 330001, 330002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(30, "BEAM3D", 30, 31, 1, 340001, 340002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(31, "BEAM3D", 31, 32, 1, 350001, 350002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(32, "BEAM3D", 32, 33, 1, 360001, 360002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(33, "BEAM3D", 33, 34, 1, 370001, 370002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(34, "BEAM3D", 34, 35, 1, 380001, 380002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(35, "BEAM3D", 35, 36, 1, 390001, 390002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(36, "BEAM3D", 36, 37, 1, 400001, 400002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(37, "BEAM3D", 37, 38, 1, 410001, 410002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(38, "BEAM3D", 38, 39, 1, 420001, 420002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(39, "BEAM3D", 39, 40, 1, 430001, 430002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(40, "BEAM3D", 40, 41, 1, 440001, 440002, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(41, "BEAM3D", 41, 42, 1, 450001, 450002, 1, 1, 0.0, 0, 0.0, 0)
    # 创建单元组
    engine.element.group.create("1_车道线单元组", "c")
    engine.element.group.create("1_车道线单元组", "a", "1to41")
    engine.element.group.create("2_车道线单元组", "c")
    engine.element.group.create("2_车道线单元组", "a", "1to41")
    engine.element.group.create("3_车道线单元组", "c")
    engine.element.group.create("3_车道线单元组", "a", "1to41")
    engine.element.group.create("4_车道线单元组", "c")
    engine.element.group.create("4_车道线单元组", "a", "1to41")
    engine.element.group.create("5_车道线单元组", "c")
    engine.element.group.create("5_车道线单元组", "a", "1to41")
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
