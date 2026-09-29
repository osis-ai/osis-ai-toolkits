"""OSIS 命令流 BOUNDARY 模块 — 边界条件(支座、约束自由度)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_boundaries(engine: OSISEngine) -> None:
    # 创建边界（便捷入口，内部转发到对应 create_* 方法）
    engine.boundary.create(1, "RIGID", 27)
    # 分配边界给节点
    engine.boundary.get(1).assign("a", 112)
    engine.boundary.create(2, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(2).assign("a", 137)
    engine.boundary.create(3, "RIGID", 31)
    engine.boundary.get(3).assign("a", 138)
    engine.boundary.create(4, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(4).assign("a", 163)
    engine.boundary.create(5, "RIGID", 77)
    engine.boundary.get(5).assign("a", 164)
    engine.boundary.create(6, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(6).assign("a", 189)
    engine.boundary.create(7, "RIGID", 81)
    engine.boundary.get(7).assign("a", 190)
    engine.boundary.create(8, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(8).assign("a", 215)
    engine.boundary.create(9, "GENERAL", "", 1, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(9).assign("a", 1)
    engine.boundary.create(10, "GENERAL", "", 0, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(10).assign("a", "2to4")
    engine.boundary.create(11, "GENERAL", "", 0, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(11).assign("a", "104to106")
    engine.boundary.create(12, "GENERAL", "", 1, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(12).assign("a", 107)
    engine.boundary.create(13, "GENERAL", "", 0, 1, 1, 0, 0, 1, 0)
    engine.boundary.get(13).assign("a", 109)
    engine.boundary.create(14, "GENERAL", "", 0, 0, 1, 0, 0, 1, 0)
    engine.boundary.get(14).assign("a", 108)
    engine.boundary.create(15, "GENERAL", "", 0, 1, 1, 0, 0, 1, 0)
    engine.boundary.get(15).assign("a", 111)
    engine.boundary.create(16, "GENERAL", "", 0, 0, 1, 0, 0, 1, 0)
    engine.boundary.get(16).assign("a", 110)
    # 创建边界组
    engine.boundary.group.create("墩底固定点", "c")
    engine.boundary.group.create("墩底固定点", "a", 2, 4, 6, 8)
    engine.boundary.group.create("墩梁固结", "c")
    engine.boundary.group.create("墩梁固结", "a", 1, 3, 5, 7)
    engine.boundary.group.create("桥台1_横向固定_纵向释放支座", "c")
    engine.boundary.group.create("桥台1_横向固定_纵向释放支座", "a", 13)
    engine.boundary.group.create("桥台1_横向释放_纵向释放支座", "c")
    engine.boundary.group.create("桥台1_横向释放_纵向释放支座", "a", 14)
    engine.boundary.group.create("桥台2_横向固定_纵向释放支座", "c")
    engine.boundary.group.create("桥台2_横向固定_纵向释放支座", "a", 15)
    engine.boundary.group.create("桥台2_横向释放_纵向释放支座", "c")
    engine.boundary.group.create("桥台2_横向释放_纵向释放支座", "a", 16)
    engine.boundary.group.create("右边跨临时支架", "c")
    engine.boundary.group.create("右边跨临时支架", "a", "11to12")
    engine.boundary.group.create("左边跨临时支架", "c")
    engine.boundary.group.create("左边跨临时支架", "a", "9to10")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_boundaries(engine)
