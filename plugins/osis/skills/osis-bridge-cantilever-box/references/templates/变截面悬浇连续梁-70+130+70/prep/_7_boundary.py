"""OSIS 命令流 BOUNDARY 模块 — 边界条件(支座、约束自由度)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_boundaries(engine: OSISEngine) -> None:
    # 创建边界（便捷入口，内部转发到对应 create_* 方法）
    engine.boundary.create(2, "GENERAL", "", 0, 1, 1, 0, 0, 1, 0)
    engine.boundary.get(2).assign("a", 89)
    engine.boundary.create(3, "GENERAL", "", 0, 0, 1, 0, 0, 1, 0)
    engine.boundary.get(3).assign("a", 88)
    engine.boundary.create(5, "GENERAL", "", 0, 1, 1, 0, 0, 1, 0)
    engine.boundary.get(5).assign("a", 91)
    engine.boundary.create(6, "GENERAL", "", 0, 0, 1, 0, 0, 1, 0)
    engine.boundary.get(6).assign("a", 90)
    engine.boundary.create(7, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(7).assign("a", 24)
    engine.boundary.create(9, "GENERAL", "", 1, 1, 1, 1, 0, 1, 0)
    engine.boundary.get(9).assign("a", 93)
    engine.boundary.create(10, "GENERAL", "", 1, 0, 1, 1, 0, 1, 0)
    engine.boundary.get(10).assign("a", 92)
    engine.boundary.create(11, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(11).assign("a", 64)
    engine.boundary.create(13, "GENERAL", "", 0, 1, 1, 0, 0, 1, 0)
    engine.boundary.get(13).assign("a", 95)
    engine.boundary.create(14, "GENERAL", "", 0, 0, 1, 0, 0, 1, 0)
    engine.boundary.get(14).assign("a", 94)
    engine.boundary.create(15, "GENERAL", "", 1, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(15).assign("a", 1)
    engine.boundary.create(16, "GENERAL", "", 0, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(16).assign("a", "2to4")
    engine.boundary.create(17, "GENERAL", "", 0, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(17).assign("a", "84to86")
    engine.boundary.create(18, "GENERAL", "", 1, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(18).assign("a", 87)
    # 创建边界组
    engine.boundary.group.create("桥墩1_横向固定_纵向释放支座", "c")
    engine.boundary.group.create("桥墩1_横向固定_纵向释放支座", "a", 5)
    engine.boundary.group.create("桥墩1_横向释放_纵向释放支座", "c")
    engine.boundary.group.create("桥墩1_横向释放_纵向释放支座", "a", 6)
    engine.boundary.group.create("桥墩1临时支架", "c")
    engine.boundary.group.create("桥墩1临时支架", "a", 7)
    engine.boundary.group.create("桥墩2_横向固定_纵向固定支座", "c")
    engine.boundary.group.create("桥墩2_横向固定_纵向固定支座", "a", 9)
    engine.boundary.group.create("桥墩2_横向释放_纵向固定支座", "c")
    engine.boundary.group.create("桥墩2_横向释放_纵向固定支座", "a", 10)
    engine.boundary.group.create("桥墩2临时支架", "c")
    engine.boundary.group.create("桥墩2临时支架", "a", 11)
    engine.boundary.group.create("桥台1_横向固定_纵向释放支座", "c")
    engine.boundary.group.create("桥台1_横向固定_纵向释放支座", "a", 2)
    engine.boundary.group.create("桥台1_横向释放_纵向释放支座", "c")
    engine.boundary.group.create("桥台1_横向释放_纵向释放支座", "a", 3)
    engine.boundary.group.create("桥台2_横向固定_纵向释放支座", "c")
    engine.boundary.group.create("桥台2_横向固定_纵向释放支座", "a", 13)
    engine.boundary.group.create("桥台2_横向释放_纵向释放支座", "c")
    engine.boundary.group.create("桥台2_横向释放_纵向释放支座", "a", 14)
    engine.boundary.group.create("右边跨临时支架", "c")
    engine.boundary.group.create("右边跨临时支架", "a", "17to18")
    engine.boundary.group.create("左边跨临时支架", "c")
    engine.boundary.group.create("左边跨临时支架", "a", "15to16")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_boundaries(engine)
