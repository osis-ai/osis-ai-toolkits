"""OSIS 命令流 ANALYSIS 模块 — 分析设置(活载等级、车道)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_analysis(engine: OSISEngine) -> None:
    # 创建活载等级（便捷入口，内部转发到对应 create_* 方法）
    engine.live.grade.create("简支变连续小箱梁移动荷载", "JTGD60_2015", "HIGHWAY_I")
    # 创建车道（便捷入口，内部转发到对应 create_* 方法）
    engine.live.lane.create("车道", "VE", 19.51, 1.8, 1, 0, "主梁单元", 0.0, 0.0)
    # 创建活载工况
    engine.live.case.create("车道荷载包络", "JTGD60_2015", 1)
    # 设置活载工况的横向布载折减系数
    engine.live.case.get("车道荷载包络").set_trans_reduction_factors(1.2, 1.0, 0.78, 0.67, 0.6, 0.55, 0.52, 0.5, 0.5, 0.5)
    # 活载子工况增删改（对应 OSIS 命令 LiveAnalInc）。
    # scalar=横向分布系数(中梁典型 0.65)
    engine.live.case.get("车道荷载包络").include("a", "车道荷载工况1", "简支变连续小箱梁移动荷载", 0.65, 1, "CUSTOM", 15.2258, "车道")
    # 设置活载子工况的加载车道数范围
    engine.live.case.get("车道荷载包络").set_lane_count("车道荷载工况1", 0, 1)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_analysis(engine)
