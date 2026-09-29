"""OSIS 命令流 BOUNDARY 模块 — 边界条件(支座、约束自由度)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_boundaries(engine: OSISEngine) -> None:
    # 创建边界（便捷入口，内部转发到对应 create_* 方法）
    engine.boundary.create(1, "GENERAL", "", 1, 1, 1, 1, 0, 1, 0)
    # 分配边界给节点
    engine.boundary.get(1).assign("a", 4)
    engine.boundary.create(2, "GENERAL", "", 0, 1, 1, 0, 0, 0, 0)
    engine.boundary.get(2).assign("a", 2, 5, 7)
    # 创建边界组
    engine.boundary.group.create("成桥", "c")
    engine.boundary.group.create("成桥", "a", "1to2")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_boundaries(engine)
