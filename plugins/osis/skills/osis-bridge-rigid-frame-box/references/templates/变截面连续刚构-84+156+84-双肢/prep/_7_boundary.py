"""OSIS 命令流 BOUNDARY 模块 — 边界条件(支座、约束自由度)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_boundaries(engine: OSISEngine) -> None:
    # 创建边界（便捷入口，内部转发到对应 create_* 方法）
    # 桥台永久支座直接约束主梁节点。原 .out 把 GENERAL 打在偏置虚节点 181–184 上,
    # 又用 RIGID 把它们设为梁端 2/177 的从节点;合拢阶段两组同时激活时从节点 Fz 重复约束,Solve 失败。
    engine.boundary.create(1, "GENERAL", "", 0, 1, 1, 0, 0, 0, 0)
    engine.boundary.get(1).assign("a", 1, 178)
    engine.boundary.create(2, "GENERAL", "", 0, 0, 1, 0, 0, 0, 0)
    engine.boundary.get(2).assign("a", 2, 177)
    engine.boundary.create(3, "GENERAL", "", 1, 1, 1, 0, 0, 0, 0)
    engine.boundary.get(3).assign("a", "1to3", "176to178")
    engine.boundary.create(4, "GENERAL", "", 1, 1, 1, 1, 1, 1, 0)
    engine.boundary.get(4).assign("a", 23, 48, 110, 135)
    engine.boundary.create(5, "RIGID", 43)
    engine.boundary.get(5).assign("a", 44)
    engine.boundary.create(6, "RIGID", 68)
    engine.boundary.get(6).assign("a", 69)
    engine.boundary.create(7, "RIGID", 130)
    engine.boundary.get(7).assign("a", 131)
    engine.boundary.create(8, "RIGID", 155)
    engine.boundary.get(8).assign("a", 156)
    engine.boundary.group.create("边墩永久支座", "c")
    engine.boundary.group.create("边墩永久支座", "a", "1to2")
    engine.boundary.group.create("边跨现浇段临时支架", "c")
    engine.boundary.group.create("边跨现浇段临时支架", "a", 3)
    engine.boundary.group.create("弹性连接", "c")
    engine.boundary.group.create("墩底固结", "c")
    engine.boundary.group.create("墩底固结", "a", 4)
    engine.boundary.group.create("墩梁固结", "c")
    engine.boundary.group.create("墩梁固结", "a", "5to8")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_boundaries(engine)
