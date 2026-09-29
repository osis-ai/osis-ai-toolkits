"""OSIS 命令流 BOUNDARY 模块 — 边界条件(支座、约束自由度)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine


def build_boundaries(engine: OSISEngine) -> None:
    # 临时支架打在主梁节点上;合拢后的永久支座也打在主梁上。
    # 原 .out 把 GENERAL 打在偏置虚节点 2/4/114/116 上,又用 RIGID 把它们设为梁端 3/115 的从节点,
    # 合拢阶段两组同时激活时从节点 Fz 重复约束,Solve 失败。
    engine.boundary.create(1, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(1).assign("a", 1, 3, 5, 113, 115, 117)
    engine.boundary.create(2, "GENERAL", "", 0, 0, 1, 0, 0, 0, 0)
    engine.boundary.get(2).assign("a", 3, 115)
    engine.boundary.create(3, "GENERAL", "", 0, 1, 1, 0, 0, 0, 0)
    engine.boundary.get(3).assign("a", 1, 117)
    engine.boundary.create(4, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(4).assign("a", 22, 35, 80, 89)
    engine.boundary.create(5, "RIGID", 33)
    engine.boundary.get(5).assign("a", 32)
    engine.boundary.create(6, "RIGID", 46)
    engine.boundary.get(6).assign("a", 45)
    engine.boundary.create(7, "RIGID", 87)
    engine.boundary.get(7).assign("a", 86)
    engine.boundary.create(8, "RIGID", 96)
    engine.boundary.get(8).assign("a", 95)
    engine.boundary.group.create("边墩永久支座", "c")
    engine.boundary.group.create("边墩永久支座", "a", "2to3")
    engine.boundary.group.create("边跨现浇段临时支架", "c")
    engine.boundary.group.create("边跨现浇段临时支架", "a", 1)
    engine.boundary.group.create("弹性连接", "c")
    engine.boundary.group.create("墩底固结", "c")
    engine.boundary.group.create("墩底固结", "a", 4)
    engine.boundary.group.create("墩梁固结", "c")
    engine.boundary.group.create("墩梁固结", "a", "5to8")


if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_boundaries(engine)
