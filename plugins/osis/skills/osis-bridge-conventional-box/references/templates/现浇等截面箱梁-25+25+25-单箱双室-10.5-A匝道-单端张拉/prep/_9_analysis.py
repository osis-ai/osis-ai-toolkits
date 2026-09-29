"""OSIS 命令流 ANALYSIS 模块 — 分析设置(活载等级、车道)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_analysis(engine: OSISEngine) -> None:
    # 创建或修改沉降组
    engine.settlement.group.create(1, -5.0, 2, 26, 51, 75)
    # 创建沉降荷载工况
    engine.settlement.create("支座沉降")
    # 将沉降组添加至当前工况
    engine.settlement.get("支座沉降").include("a", 1)
    # 创建活载等级（便捷入口，内部转发到对应 create_* 方法）
    engine.live.grade.create("CH-CD", "JTGD60_2015", "HIGHWAY_I")
    # 创建车道（便捷入口，内部转发到对应 create_* 方法）
    engine.live.lane.create("1_", "VE", 20.0, 1.8, 1, 0, "1_车道线单元组", 3.35, 0.0)
    engine.live.lane.create("2_", "VE", 20.0, 1.8, 1, 0, "2_车道线单元组", 0.25, 0.0)
    engine.live.lane.create("3_", "VE", 20.0, 1.8, 1, 0, "3_车道线单元组", -2.85, 0.0)
    # 创建活载工况
    engine.live.case.create("公路一级", "JTGD60_2015", 1)
    # 设置活载工况的横向布载折减系数
    engine.live.case.get("公路一级").set_trans_reduction_factors(1.2, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    # 活载子工况增删改（对应 OSIS 命令 LiveAnalInc）。
    engine.live.case.get("公路一级").include("a", "公路一级_sub1", "CH-CD", 1.0, 1, "CUSTOM", 0.85, "1_", "2_", "3_")
    # 设置活载子工况的加载车道数范围
    engine.live.case.get("公路一级").set_lane_count("公路一级_sub1", 0, 3)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_analysis(engine)
