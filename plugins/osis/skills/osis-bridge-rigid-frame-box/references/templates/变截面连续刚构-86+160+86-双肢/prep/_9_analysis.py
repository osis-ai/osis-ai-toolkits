"""OSIS 命令流 ANALYSIS 模块 — 分析设置(活载等级、车道)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_analysis(engine: OSISEngine) -> None:
    # 创建或修改沉降组
    engine.settlement.group.create("桥墩1沉降组", -0.015, 137, 163)
    engine.settlement.group.create("桥墩2沉降组", -0.015, 189, 215)
    engine.settlement.group.create("桥台1沉降组", -0.01, 108, 109)
    engine.settlement.group.create("桥台2沉降组", -0.01, 110, 111)
    # 创建沉降荷载工况
    engine.settlement.create("沉降")
    # 将沉降组添加至当前工况
    engine.settlement.get("沉降").include("a", "桥墩1沉降组", "桥墩2沉降组", "桥台1沉降组", "桥台2沉降组")
    # 创建活载等级（便捷入口，内部转发到对应 create_* 方法）
    engine.live.grade.create("变截面悬浇梁移动荷载", "JTGD60_2015", "HIGHWAY_I")
    # 创建车道（便捷入口，内部转发到对应 create_* 方法）
    engine.live.lane.create("右偏载工况车道1", "VE", 160.0, 1.8, 1, 0, "主梁单元", -4.475, 0.0)
    engine.live.lane.create("右偏载工况车道2", "VE", 160.0, 1.8, 1, 0, "主梁单元", -1.375, 0.0)
    engine.live.lane.create("中载工况车道1", "VE", 160.0, 1.8, 1, 0, "主梁单元", -1.55, 0.0)
    engine.live.lane.create("中载工况车道2", "VE", 160.0, 1.8, 1, 0, "主梁单元", 1.55, 0.0)
    engine.live.lane.create("左偏载工况车道1", "VE", 160.0, 1.8, 1, 0, "主梁单元", 4.475, 0.0)
    engine.live.lane.create("左偏载工况车道2", "VE", 160.0, 1.8, 1, 0, "主梁单元", 1.375, 0.0)
    # 创建活载工况
    engine.live.case.create("右偏载工况", "JTGD60_2015", 1)
    # 设置活载工况的横向布载折减系数
    engine.live.case.get("右偏载工况").set_trans_reduction_factors(1.2, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    # 活载子工况增删改（对应 OSIS 命令 LiveAnalInc）。
    engine.live.case.get("右偏载工况").include("a", "右偏车道荷载子工况", "变截面悬浇梁移动荷载", 1.3, 1, "CUSTOM", 1.35, "右偏载工况车道1", "右偏载工况车道2")
    # 设置活载子工况的加载车道数范围
    engine.live.case.get("右偏载工况").set_lane_count("右偏车道荷载子工况", 0, 2)
    engine.live.case.create("中载工况", "JTGD60_2015", 1)
    engine.live.case.get("中载工况").set_trans_reduction_factors(1.2, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    engine.live.case.get("中载工况").include("a", "中载车道荷载子工况", "变截面悬浇梁移动荷载", 1.3, 1, "CUSTOM", 1.35, "中载工况车道1", "中载工况车道2")
    engine.live.case.get("中载工况").set_lane_count("中载车道荷载子工况", 0, 2)
    engine.live.case.create("左偏载工况", "JTGD60_2015", 1)
    engine.live.case.get("左偏载工况").set_trans_reduction_factors(1.2, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    engine.live.case.get("左偏载工况").include("a", "左偏车道荷载子工况", "变截面悬浇梁移动荷载", 1.3, 1, "CUSTOM", 1.35, "左偏载工况车道1", "左偏载工况车道2")
    engine.live.case.get("左偏载工况").set_lane_count("左偏车道荷载子工况", 0, 2)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_analysis(engine)
