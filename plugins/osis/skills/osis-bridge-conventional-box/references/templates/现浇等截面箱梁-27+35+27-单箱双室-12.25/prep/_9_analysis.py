"""OSIS 命令流 ANALYSIS 模块 — 分析设置(活载等级、车道)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_analysis(engine: OSISEngine) -> None:
    # 创建或修改沉降组
    engine.settlement.group.create("沉降组1", 0.005, 100, 104)
    engine.settlement.group.create("沉降组2", 0.005, 101, 105)
    engine.settlement.group.create("沉降组3", 0.005, 102, 106)
    engine.settlement.group.create("沉降组4", 0.005, 103, 107)
    # 创建沉降荷载工况
    engine.settlement.create("支座沉降荷载工况")
    # 将沉降组添加至当前工况
    engine.settlement.get("支座沉降荷载工况").include("a", "沉降组1", "沉降组2", "沉降组3", "沉降组4")
    # 创建活载等级（便捷入口，内部转发到对应 create_* 方法）
    engine.live.grade.create("CH-CD", "JTGD60_2015", "HIGHWAY_I")
    # 创建车道（便捷入口，内部转发到对应 create_* 方法）
    engine.live.lane.create("车道1", "VE", 35.0, 1.8, 1, 0, "车道1车道线单元组", 4.45, 0.0)
    engine.live.lane.create("车道2", "VE", 35.0, 1.8, 1, 0, "车道2车道线单元组", 1.3, 0.0)
    engine.live.lane.create("车道3", "VE", 35.0, 1.8, 1, 0, "车道3车道线单元组", -1.85, 0.0)
    # 创建活载工况
    engine.live.case.create("移动荷载工况", "JTGD60_2015", 1)
    # 设置活载工况的横向布载折减系数
    engine.live.case.get("移动荷载工况").set_trans_reduction_factors(1.2, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    # 活载子工况增删改（对应 OSIS 命令 LiveAnalInc）。
    engine.live.case.get("移动荷载工况").include("a", "移动荷载工况_sub1", "CH-CD", 1.0, 1, "CUSTOM", 0.85, "车道1", "车道2", "车道3")
    # 设置活载子工况的加载车道数范围
    engine.live.case.get("移动荷载工况").set_lane_count("移动荷载工况_sub1", 0, 3)
    # 创建或修改荷载转换质量总体信息。
    engine.dynamic.load_to_mass.create("荷载转换质量_二期_二期")
    # 添加荷载转换质量项。
    engine.dynamic.load_to_mass.get("荷载转换质量_二期_二期").add("二期_二期", 1.0, 9.806, 0, 0, 0, 1, 1, 1)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_analysis(engine)
