"""OSIS 命令流 STAGE 模块 — 施工阶段(激活/钝化、体系转换)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_stages(engine: OSISEngine) -> None:
    # 创建施工阶段
    engine.stage.create(1, "自重", 30.0)
    # 通过单元组激活/钝化单元
    engine.stage.get(1).define_element(1, 1, "结构组_1", 3.0, 0)
    # 通过边界组激活/钝化边界
    engine.stage.get(1).define_boundary(1, 1, "弹性连接")
    engine.stage.get(1).define_boundary(1, 1, "一般支撑")
    # 激活/钝化荷载工况
    engine.stage.get(1).define_loadcase(1, 1, "", "自重自重")
    engine.stage.get(1).define_loadcase(1, 1, "", "预应力_预应力")
    engine.stage.create(2, "二期", 30.0)
    engine.stage.get(2).define_loadcase(1, 1, "", "二期_二期")
    engine.stage.create(3, "成桥", 3650.0)
    engine.stage.create(4, "运营", 0.0)
    engine.stage.get(4).define_loadcase(1, 1, "", "整体升温_整体升温")
    engine.stage.get(4).define_loadcase(1, 1, "", "整体降温_整体降温")
    engine.stage.get(4).define_loadcase(1, 1, "", "梯度升温_梯度升温")
    engine.stage.get(4).define_loadcase(1, 1, "", "梯度降温_梯度降温")
    # 激活分析工况,分析工况默认在每个施工阶段的静力工况之后，不同分析工况无先后顺序
    engine.stage.get(4).define_analysis(1, "MODAL", "")
    engine.stage.get(4).define_analysis(1, "SETL", "支座沉降荷载工况")
    engine.stage.get(4).define_analysis(1, "LTM", "荷载转换质量_二期_二期")
    engine.stage.get(4).define_analysis(1, "LIVE", "移动荷载工况")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_stages(engine)
