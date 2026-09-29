"""OSIS 命令流 STAGE 模块 — 施工阶段(激活/钝化、体系转换)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_stages(engine: OSISEngine) -> None:
    # 创建施工阶段
    engine.stage.create(1, "CS1_主梁预制、张拉预应力", 7.0)
    # 通过单元组激活/钝化单元
    engine.stage.get(1).define_element(1, 1, "主梁单元", 7.0, 0)
    # 通过边界组激活/钝化边界
    engine.stage.get(1).define_boundary(1, 1, "桥台1_永久_x向固定")
    engine.stage.get(1).define_boundary(1, 1, "桥台2_永久_x向滑动")
    # 激活/钝化荷载工况
    engine.stage.get(1).define_loadcase(1, 1, "", "主梁单元自重")
    engine.stage.get(1).define_loadcase(1, 1, "", "预应力")
    engine.stage.get(1).define_loadcase(1, 1, "", "端横梁荷载工况")
    engine.stage.get(1).define_loadcase(1, 1, "", "中横梁荷载工况")
    engine.stage.create(2, "CS2_存梁", 60.0)
    engine.stage.create(3, "CS3_二期恒载", 30.0)
    engine.stage.get(3).define_loadcase(1, 1, "", "铺装工况")
    engine.stage.get(3).define_loadcase(1, 1, "", "防撞护栏工况")
    engine.stage.create(4, "CS4_徐变十年", 3650.0)
    engine.stage.create(5, "CS5_运营阶段", 0.0)
    engine.stage.get(5).define_loadcase(1, 1, "", "整体升温")
    engine.stage.get(5).define_loadcase(1, 1, "", "整体降温")
    engine.stage.get(5).define_loadcase(1, 1, "", "正温度梯度")
    engine.stage.get(5).define_loadcase(1, 1, "", "负温度梯度")
    # 激活分析工况,分析工况默认在每个施工阶段的静力工况之后，不同分析工况无先后顺序
    engine.stage.get(5).define_analysis(1, "LIVE", "车道荷载包络")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_stages(engine)
