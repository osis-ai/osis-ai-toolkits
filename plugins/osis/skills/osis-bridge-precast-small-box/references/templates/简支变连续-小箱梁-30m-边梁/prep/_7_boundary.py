"""OSIS 命令流 BOUNDARY 模块 — 边界条件(支座、约束自由度)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_boundaries(engine: OSISEngine) -> None:
    # 创建边界（便捷入口，内部转发到对应 create_* 方法）
    engine.boundary.create(1, "GENERAL", "", 1, 1, 1, 1, 0, 1, 0)
    # 分配边界给节点
    engine.boundary.get(1).assign("a", 2, 26, 50)
    engine.boundary.create(2, "GENERAL", "", 0, 1, 1, 1, 0, 1, 0)
    engine.boundary.get(2).assign("a", 22, 46, 70)
    engine.boundary.create(3, "GENERAL", "", 0, 1, 1, 1, 0, 1, 0)
    engine.boundary.get(3).assign("a", 2)
    engine.boundary.create(4, "GENERAL", "", 1, 1, 1, 1, 0, 1, 0)
    engine.boundary.get(4).assign("a", 24)
    engine.boundary.create(5, "GENERAL", "", 0, 1, 1, 1, 0, 1, 0)
    engine.boundary.get(5).assign("a", 48)
    engine.boundary.create(6, "GENERAL", "", 0, 1, 1, 1, 0, 1, 0)
    engine.boundary.get(6).assign("a", 70)
    # 创建边界组
    engine.boundary.group.create("临时支座-右", "c")
    engine.boundary.group.create("临时支座-右", "a", 2)
    engine.boundary.group.create("临时支座-左", "c")
    engine.boundary.group.create("临时支座-左", "a", 1)
    engine.boundary.group.create("桥墩1_永久_x向固定", "c")
    engine.boundary.group.create("桥墩1_永久_x向固定", "a", 4)
    engine.boundary.group.create("桥墩2_永久_x向滑动", "c")
    engine.boundary.group.create("桥墩2_永久_x向滑动", "a", 5)
    engine.boundary.group.create("桥台1_永久_x向滑动", "c")
    engine.boundary.group.create("桥台1_永久_x向滑动", "a", 3)
    engine.boundary.group.create("桥台2_永久_x向滑动", "c")
    engine.boundary.group.create("桥台2_永久_x向滑动", "a", 6)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_boundaries(engine)
