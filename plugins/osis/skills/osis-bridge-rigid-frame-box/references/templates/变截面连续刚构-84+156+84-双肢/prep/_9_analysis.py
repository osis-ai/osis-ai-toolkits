"""OSIS 命令流 ANALYSIS 模块 — 分析设置(活载等级、车道)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_analysis(engine: OSISEngine) -> None:
    # 创建或修改沉降组
    engine.settlement.group.create("支座沉降组1", -0.01, 23, 48)
    engine.settlement.group.create("支座沉降组2", -0.01, 110, 135)
    engine.settlement.group.create("支座沉降组3", -0.01, 1, 2)
    engine.settlement.group.create("支座沉降组4", -0.01, 177, 178)
    # 创建沉降荷载工况
    engine.settlement.create("支座沉降")
    # 向当前沉降工况添加或移除沉降组
    engine.settlement.get("支座沉降").include("a", "支座沉降组1", "支座沉降组2", "支座沉降组3", "支座沉降组4")
    # 创建活载等级（便捷入口，内部转发到对应 create_* 方法）
    engine.live.grade.create("CH-CD", "JTGD60_2015", "HIGHWAY_I")
    # 创建车道（便捷入口，内部转发到对应 create_* 方法）
    engine.live.lane.create("车道1", "VE", 156.0, 1.8, 1, 0, "车道1车道线单元组", -2.5, 0.0)
    engine.live.lane.create("车道2", "VE", 156.0, 1.8, 1, 0, "车道2车道线单元组", 2.5, 0.0)
    # 创建活载工况
    engine.live.case.create("移动荷载", "JTGD60_2015", 1)
    # 设置活载工况的横向布载折减系数。
    engine.live.case.get("移动荷载").set_trans_reduction_factors(1.2, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    # 活载子工况增删改（对应 OSIS 命令 LiveAnalInc）。
    engine.live.case.get("移动荷载").include("a", "移动荷载_sub1", "CH-CD", 1.15, 1, "CUSTOM", 0.976099, "车道1", "车道2")
    # 设置活载子工况的加载车道数范围
    engine.live.case.get("移动荷载").set_lane_count("移动荷载_sub1", 0, 2)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_analysis(engine)
