"""OSIS 命令流 ANALYSIS 模块 — 分析设置(活载等级、车道)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_analysis(engine: OSISEngine) -> None:
    # 创建或修改沉降组
    engine.settlement.group.create(1, -0.01, 204, 205)
    engine.settlement.group.create(3, -0.01, 253, 271)
    engine.settlement.group.create(4, -0.01, 290, 309)
    engine.settlement.group.create(5, -0.01, 328, 347)
    engine.settlement.group.create(6, -0.01, 366, 385)
    engine.settlement.group.create(8, -0.01, 422, 423)
    # 创建沉降荷载工况
    engine.settlement.create("支座沉降")
    # 向当前沉降工况添加或移除沉降组
    engine.settlement.get("支座沉降").include("a", 1, 3, 4, 5, 6, 8)
    # 创建活载等级（便捷入口，内部转发到对应 create_* 方法）
    engine.live.grade.create("CH-CD", "JTGD60_2015", "HIGHWAY_I")
    # 创建车道（便捷入口，内部转发到对应 create_* 方法）
    engine.live.lane.create("车道1", "VE", 100.0, 1.8, 1, 0, "车道1车道线单元组", -4.4625, 0.0)
    engine.live.lane.create("车道2", "VE", 100.0, 1.8, 1, 0, "车道2车道线单元组", -1.3625, 0.0)
    engine.live.lane.create("车道3", "VE", 100.0, 1.8, 1, 0, "车道3车道线单元组", 1.7375, 0.0)
    # 创建活载工况
    engine.live.case.create("汽车荷载", "JTGD60_2015", 0)
    # 设置活载工况的横向布载折减系数。
    engine.live.case.get("汽车荷载").set_trans_reduction_factors(1.2, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    # 活载子工况增删改（对应 OSIS 命令 LiveAnalInc）。
    engine.live.case.get("汽车荷载").include("a", "汽车荷载_sub1", "CH-CD", 1.495, 1, "CUSTOM", 1.28, "车道1", "车道2", "车道3")
    # 设置活载子工况的加载车道数范围
    engine.live.case.get("汽车荷载").set_lane_count("汽车荷载_sub1", 0, 3)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_analysis(engine)
