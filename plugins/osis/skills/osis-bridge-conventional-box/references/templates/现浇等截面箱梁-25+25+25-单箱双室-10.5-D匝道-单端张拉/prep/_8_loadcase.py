"""OSIS 命令流 LOADCASE 模块 — 荷载工况(自重、二期、预应力、温度、沉降)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_loadcases(engine: OSISEngine) -> None:
    # 创建钢束特性（便捷入口，内部转发到对应 create_* 方法）
    engine.tendon.prop.create("15-19", "IN", 2, 0, 0.00266, 0.122, 0.2, 0.0015, 0.006, 0.006, 1.0, 0.3)
    # 创建钢束形状（便捷入口，内部转发到对应 create_* 方法）
    engine.tendon.shape.create("B1", 6, "15-19", "B1单元组", "ARC3D", "钢束样条曲线_B1")
    # 布置钢束形状
    engine.tendon.shape.get("B1").layout("GLOBAL")
    engine.tendon.shape.create("B2", 6, "15-19", "B2单元组", "ARC3D", "钢束样条曲线_B2")
    engine.tendon.shape.get("B2").layout("GLOBAL")
    # 创建荷载工况
    engine.load.create("二期_二期", "CS", 1.0)
    for i in range(1, 76):
        engine.load.get("二期_二期").create("LINE", i, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -68800.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -68800.0, 0.0, 0.0, 0.0)
    engine.load.create("横隔板_横隔板", "CS", 1.0)
    engine.load.get("横隔板_横隔板").create("NFORCE", 77, 0.0, 0.0, -57375.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("NFORCE", 78, 0.0, 0.0, -57375.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("NFORCE", 79, 0.0, 0.0, -57375.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("NFORCE", 80, 0.0, 0.0, -57375.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("NFORCE", 81, 0.0, 0.0, -57375.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("NFORCE", 82, 0.0, 0.0, -57375.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("LINE", 1, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("LINE", 2, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("LINE", 25, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("LINE", 26, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("LINE", 50, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("LINE", 51, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("LINE", 74, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0)
    engine.load.get("横隔板_横隔板").create("LINE", 75, 1, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -114750.0, 0.0, 0.0, 0.0)
    engine.load.create("降温_降温", "T", 1.0)
    for i in range(1, 76):
        engine.load.get("降温_降温").create("UTEMP", i, "X", -25.0)
    engine.load.create("升温_升温", "T", 1.0)
    for i in range(1, 76):
        engine.load.get("升温_升温").create("UTEMP", i, "X", 20.0)
    engine.load.create("梯度降温_梯度降温", "TG", 1.0)
    for i in range(1, 76):
        engine.load.get("梯度降温_梯度降温").create("GTEMP", i, "Z", "T", 2, 10.5, 0.0, -7.0, -0.1, -2.75, 7.611, -0.1, -2.75, -0.4, 0.0)
    engine.load.create("梯度升温_梯度升温", "TG", 1.0)
    for i in range(1, 76):
        engine.load.get("梯度升温_梯度升温").create("GTEMP", i, "Z", "T", 2, 10.5, 0.0, 14.0, -0.1, 5.5, 7.611, -0.1, 5.5, -0.4, 0.0)
    engine.load.create("一次落架自重", "CS", 1.0)
    engine.load.get("一次落架自重").create("GRAVITY", 0.0, 0.0, -1.04)
    engine.load.create("预应力_预应力", "CS", 1.0)
    engine.load.get("预应力_预应力").create("PST", "B1", "END", "ST", 1395000000.0)
    engine.load.get("预应力_预应力").create("PST", "B2", "END", "ST", 1395000000.0)
    engine.load.create("自重_自重", "CS", 1.0)
    engine.load.get("自重_自重").create("GRAVITY", 0.0, 0.0, -1.04)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_loadcases(engine)
