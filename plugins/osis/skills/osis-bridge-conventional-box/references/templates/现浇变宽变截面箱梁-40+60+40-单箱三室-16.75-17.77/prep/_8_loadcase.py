"""OSIS 命令流 LOADCASE 模块 — 荷载工况(自重、二期、预应力、温度、沉降)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_loadcases(engine: OSISEngine) -> None:
    # 创建钢束特性（便捷入口，内部转发到对应 create_* 方法）
    engine.tendon.prop.create("15-17", "IN", 2, 0, 0.00238, 0.106, 0.2, 0.0015, 0.006, 0.006, 1.0, 1.0)
    engine.tendon.prop.create("15-22", "IN", 2, 0, 0.00308, 0.12, 0.2, 0.0015, 0.006, 0.006, 1.0, 1.0)
    # 创建钢束形状（便捷入口，内部转发到对应 create_* 方法）
    engine.tendon.shape.create("1_", 8, "15-22", "1_单元组", "ARC2D", 1, "钢束竖弯样条曲线_1_", "钢束平弯样条曲线_1_")
    # 布置钢束形状
    engine.tendon.shape.get("1_").layout("GLOBAL")
    engine.tendon.shape.create("2_", 8, "15-22", "2_单元组", "ARC2D", 1, "钢束竖弯样条曲线_2_", "钢束平弯样条曲线_2_")
    engine.tendon.shape.get("2_").layout("GLOBAL")
    engine.tendon.shape.create("3_", 8, "15-22", "3_单元组", "ARC2D", 1, "钢束竖弯样条曲线_3_", "钢束平弯样条曲线_3_")
    engine.tendon.shape.get("3_").layout("GLOBAL")
    # 创建荷载工况
    engine.load.create("二期_二期", "CS", 1.0)
    for i in range(1, 137):
        engine.load.get("二期_二期").create("LINE", i, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -103600.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -103600.0, 0.0, 0.0, 0.0)
    engine.load.create("降温_降温", "T", 1.0)
    for i in range(1, 137):
        engine.load.get("降温_降温").create("UTEMP", i, "X", -25.0)
    engine.load.create("升温_升温", "T", 1.0)
    for i in range(1, 137):
        engine.load.get("升温_升温").create("UTEMP", i, "X", 20.0)
    engine.load.create("梯度降温_梯度降温", "TG", 1.0)
    for i in range(1, 137):
        engine.load.get("梯度降温_梯度降温").create("GTEMP", i, "Z", "T", 2, 18.0, 0.0, -7.0, -0.1, -2.75, 15.49, -0.1, -2.75, -0.4, 0.0)
    engine.load.create("梯度升温_梯度升温", "TG", 1.0)
    for i in range(1, 137):
        engine.load.get("梯度升温_梯度升温").create("GTEMP", i, "Z", "T", 2, 18.0, 0.0, 14.0, -0.1, 5.5, 15.49, -0.1, 5.5, -0.4, 0.0)
    engine.load.create("预应力_预应力", "CS", 1.0)
    engine.load.get("预应力_预应力").create("PST", "1_", "BOTH", "ST", 1395000000.0, 1395000000.0)
    engine.load.get("预应力_预应力").create("PST", "2_", "BOTH", "ST", 1395000000.0, 1395000000.0)
    engine.load.get("预应力_预应力").create("PST", "3_", "BOTH", "ST", 1395000000.0, 1395000000.0)
    engine.load.create("支架现浇自重", "CS", 1.0)
    engine.load.get("支架现浇自重").create("GRAVITY", 0.0, 0.0, -1.04)
    engine.load.create("自重_自重", "CS", 1.0)
    engine.load.get("自重_自重").create("GRAVITY", 0.0, 0.0, -1.04)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_loadcases(engine)
