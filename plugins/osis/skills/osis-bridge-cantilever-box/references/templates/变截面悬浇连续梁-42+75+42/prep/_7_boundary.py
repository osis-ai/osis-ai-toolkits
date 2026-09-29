"""OSIS 命令流 BOUNDARY 模块 — 边界条件(支座、约束自由度)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_boundaries(engine: OSISEngine) -> None:
    # 创建边界（便捷入口，内部转发到对应 create_* 方法）
    engine.boundary.create(1, "GENERAL", "", 0, 1, 1, 0, 0, 1, 0)
    # 分配边界给节点
    engine.boundary.get(1).assign("a", 59)
    engine.boundary.create(2, "GENERAL", "", 0, 0, 1, 0, 0, 1, 0)
    engine.boundary.get(2).assign("a", 58)
    engine.boundary.create(3, "GENERAL", "", 0, 1, 1, 0, 0, 1, 0)
    engine.boundary.get(3).assign("a", 61)
    engine.boundary.create(4, "GENERAL", "", 0, 0, 1, 0, 0, 1, 0)
    engine.boundary.get(4).assign("a", 60)
    engine.boundary.create(5, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(5).assign("a", 17)
    engine.boundary.create(6, "GENERAL", "", 1, 1, 1, 1, 0, 1, 0)
    engine.boundary.get(6).assign("a", 63)
    engine.boundary.create(7, "GENERAL", "", 1, 0, 1, 1, 0, 1, 0)
    engine.boundary.get(7).assign("a", 62)
    engine.boundary.create(8, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(8).assign("a", 41)
    engine.boundary.create(9, "GENERAL", "", 0, 1, 1, 0, 0, 1, 0)
    engine.boundary.get(9).assign("a", 65)
    engine.boundary.create(10, "GENERAL", "", 0, 0, 1, 0, 0, 1, 0)
    engine.boundary.get(10).assign("a", 64)
    engine.boundary.create(11, "GENERAL", "", 1, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(11).assign("a", 1)
    engine.boundary.create(12, "GENERAL", "", 0, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(12).assign("a", "2to5")
    engine.boundary.create(13, "GENERAL", "", 0, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(13).assign("a", "53to56")
    engine.boundary.create(14, "GENERAL", "", 1, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(14).assign("a", 57)
    # 创建边界组
    engine.boundary.group.create("桥墩1_横向固定_纵向释放支座", "c")
    engine.boundary.group.create("桥墩1_横向固定_纵向释放支座", "a", 3)
    engine.boundary.group.create("桥墩1_横向释放_纵向释放支座", "c")
    engine.boundary.group.create("桥墩1_横向释放_纵向释放支座", "a", 4)
    engine.boundary.group.create("桥墩1临时支架", "c")
    engine.boundary.group.create("桥墩1临时支架", "a", 5)
    engine.boundary.group.create("桥墩2_横向固定_纵向固定支座", "c")
    engine.boundary.group.create("桥墩2_横向固定_纵向固定支座", "a", 6)
    engine.boundary.group.create("桥墩2_横向释放_纵向固定支座", "c")
    engine.boundary.group.create("桥墩2_横向释放_纵向固定支座", "a", 7)
    engine.boundary.group.create("桥墩2临时支架", "c")
    engine.boundary.group.create("桥墩2临时支架", "a", 8)
    engine.boundary.group.create("桥台1_横向固定_纵向释放支座", "c")
    engine.boundary.group.create("桥台1_横向固定_纵向释放支座", "a", 1)
    engine.boundary.group.create("桥台1_横向释放_纵向释放支座", "c")
    engine.boundary.group.create("桥台1_横向释放_纵向释放支座", "a", 2)
    engine.boundary.group.create("桥台2_横向固定_纵向释放支座", "c")
    engine.boundary.group.create("桥台2_横向固定_纵向释放支座", "a", 9)
    engine.boundary.group.create("桥台2_横向释放_纵向释放支座", "c")
    engine.boundary.group.create("桥台2_横向释放_纵向释放支座", "a", 10)
    engine.boundary.group.create("右边跨临时支架", "c")
    engine.boundary.group.create("右边跨临时支架", "a", "13to14")
    engine.boundary.group.create("左边跨临时支架", "c")
    engine.boundary.group.create("左边跨临时支架", "a", "11to12")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_boundaries(engine)
