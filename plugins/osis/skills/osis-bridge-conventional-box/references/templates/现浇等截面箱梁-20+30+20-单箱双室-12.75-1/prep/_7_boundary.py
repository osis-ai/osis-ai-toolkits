"""OSIS 命令流 BOUNDARY 模块 — 边界条件(支座、约束自由度)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_boundaries(engine: OSISEngine) -> None:
    # 创建边界（便捷入口，内部转发到对应 create_* 方法）
    engine.boundary.create(1, "GENERAL", "", 0, 0, 1, 1, 0, 0, 0)
    # 分配边界给节点
    engine.boundary.get(1).assign("a", "104to105", 107)
    engine.boundary.create(2, "GENERAL", "", 0, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(2).assign("a", "100to101", 103)
    engine.boundary.create(3, "GENERAL", "", 1, 0, 1, 1, 0, 0, 0)
    engine.boundary.get(3).assign("a", 106)
    engine.boundary.create(4, "GENERAL", "", 1, 1, 1, 1, 0, 0, 0)
    engine.boundary.get(4).assign("a", 102)
    engine.boundary.create(5, "RIGID", 2)
    engine.boundary.get(5).assign("a", 104)
    engine.boundary.create(6, "RIGID", 2)
    engine.boundary.get(6).assign("a", 100)
    engine.boundary.create(7, "RIGID", 15)
    engine.boundary.get(7).assign("a", 105)
    engine.boundary.create(8, "RIGID", 15)
    engine.boundary.get(8).assign("a", 101)
    engine.boundary.create(9, "RIGID", 33)
    engine.boundary.get(9).assign("a", 106)
    engine.boundary.create(10, "RIGID", 33)
    engine.boundary.get(10).assign("a", 102)
    engine.boundary.create(11, "RIGID", 46)
    engine.boundary.get(11).assign("a", 107)
    engine.boundary.create(12, "RIGID", 46)
    engine.boundary.get(12).assign("a", 103)
    # 创建边界组
    engine.boundary.group.create("弹性连接", "c")
    engine.boundary.group.create("弹性连接", "a", "5to12")
    engine.boundary.group.create("一般支撑", "c")
    engine.boundary.group.create("一般支撑", "a", "1to4")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_boundaries(engine)
