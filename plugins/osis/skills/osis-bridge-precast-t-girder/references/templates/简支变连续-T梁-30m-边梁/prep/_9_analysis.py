"""OSIS 命令流 ANALYSIS 模块 — 分析设置(活载等级、车道)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_analysis(engine: OSISEngine) -> None:
    # 创建或修改沉降组
    engine.settlement.group.create("沉降组1", -0.005, 2)
    engine.settlement.group.create("沉降组2", -0.005, 23)
    engine.settlement.group.create("沉降组3", -0.005, 47)
    engine.settlement.group.create("沉降组4", -0.005, 68)
    # 创建沉降荷载工况
    engine.settlement.create("沉降工况")
    # 将沉降组添加至当前工况
    engine.settlement.get("沉降工况").include("a", "沉降组1", "沉降组2", "沉降组3", "沉降组4")
    # 创建活载等级（便捷入口，内部转发到对应 create_* 方法）
    engine.live.grade.create("简支变连续T梁移动荷载", "JTGD60_2015", "HIGHWAY_I")
    # 创建车道（便捷入口，内部转发到对应 create_* 方法）
    engine.live.lane.create("车道", "VE", 29.4, 1.8, 1, 0, "主梁单元", 0.0, 0.0)
    # 创建活载工况
    engine.live.case.create("车道荷载包络", "JTGD60_2015", 1)
    # 设置活载工况的横向布载折减系数
    engine.live.case.get("车道荷载包络").set_trans_reduction_factors(1, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    # 活载子工况增删改（对应 OSIS 命令 LiveAnalInc）。
    engine.live.case.get("车道荷载包络").include("a", "车道荷载工况1", "简支变连续T梁移动荷载", 0.8, 1, "CUSTOM", 3.492, "车道")
    # 设置活载子工况的加载车道数范围
    engine.live.case.get("车道荷载包络").set_lane_count("车道荷载工况1", 0, 1)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_analysis(engine)
