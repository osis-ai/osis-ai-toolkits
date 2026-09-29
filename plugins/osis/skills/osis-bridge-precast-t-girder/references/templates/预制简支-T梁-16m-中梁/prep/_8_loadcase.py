"""OSIS 命令流 LOADCASE 模块 — 荷载工况(自重、二期、预应力、温度、沉降)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_loadcases(engine: OSISEngine) -> None:
    # 创建钢束特性（便捷入口，内部转发到对应 create_* 方法）
    engine.tendon.prop.create("15-10", "IN", 3, 1, "GBT5224_2014", 15.2, 10, 0.09, 0.17, 0.0015, 0.006, 0.006, 1.0, 0.3)
    engine.tendon.prop.create("15-3", "IN", 3, 1, "GBT5224_2014", 15.2, 3, 0.055, 0.17, 0.0015, 0.006, 0.006, 1.0, 0.3)
    engine.tendon.prop.create("15-4", "IN", 3, 1, "GBT5224_2014", 15.2, 4, 0.055, 0.17, 0.0015, 0.006, 0.006, 1.0, 0.3)
    engine.tendon.prop.create("15-5", "IN", 3, 1, "GBT5224_2014", 15.2, 5, 0.055, 0.17, 0.0015, 0.006, 0.006, 1.0, 0.3)
    engine.tendon.prop.create("15-6", "IN", 3, 1, "GBT5224_2014", 15.2, 6, 0.07, 0.17, 0.0015, 0.006, 0.006, 1.0, 0.3)
    engine.tendon.prop.create("15-7", "IN", 3, 1, "GBT5224_2014", 15.2, 7, 0.07, 0.17, 0.0015, 0.006, 0.006, 1.0, 0.3)
    engine.tendon.prop.create("15-8", "IN", 3, 1, "GBT5224_2014", 15.2, 8, 0.07, 0.17, 0.0015, 0.006, 0.006, 1.0, 0.3)
    engine.tendon.prop.create("15-9", "IN", 3, 1, "GBT5224_2014", 15.2, 9, 0.09, 0.17, 0.0015, 0.006, 0.006, 1.0, 0.3)
    # 创建钢束形状（便捷入口，内部转发到对应 create_* 方法）
    engine.tendon.shape.create("N1", 1, "15-9", "钢束-1-N1线型单元", "ARC3D", "钢束-1-N1")
    # 布置钢束形状
    engine.tendon.shape.get("N1").layout("ELEMENT", 1, 0, 0, 0.0, 0.0, 0.0)
    engine.tendon.shape.create("N2", 1, "15-9", "钢束-2-N2线型单元", "ARC3D", "钢束-2-N2")
    engine.tendon.shape.get("N2").layout("ELEMENT", 1, 0, 0, 0.0, 0.0, 0.0)
    # 创建荷载工况
    engine.load.create("端横梁荷载工况", "CS", 1.0)
    engine.load.get("端横梁荷载工况").create("NFORCE", 2, 0.0, 0.0, -5850.0, 0.0, 0.0, 0.0)
    engine.load.get("端横梁荷载工况").create("NFORCE", 18, 0.0, 0.0, -5850.0, 0.0, 0.0, 0.0)
    engine.load.create("防撞护栏工况", "CS", 1.0)
    for i in range(1, 19):
        engine.load.get("防撞护栏工况").create("LINE", i, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -2120.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -2120.0, 0.0, 0.0, 0.0)
    engine.load.create("负温度梯度", "TG", 1.0)
    for i in range(1, 19):
        engine.load.get("负温度梯度").create("GTEMP", i, "Z", "T", 2, 1.2, 0.0, -7.0, -0.1, -2.75, 0.679, -0.1, -2.75, -0.4, 0.0)
    engine.load.create("铺装工况", "CS", 1.0)
    for i in range(1, 19):
        engine.load.get("铺装工况").create("LINE", i, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, -8000.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -8000.0, 0.0, 0.0, 0.0)
    engine.load.create("预应力", "CS", 1.0)
    engine.load.get("预应力").create("PST", "N1", "BOTH", "ST", 1395000000.0, 1395000000.0)
    engine.load.get("预应力").create("PST", "N2", "BOTH", "ST", 1395000000.0, 1395000000.0)
    engine.load.create("整体降温", "T", 1.0)
    for i in range(1, 19):
        engine.load.get("整体降温").create("UTEMP", i, "X", -20.0)
    engine.load.create("整体升温", "T", 1.0)
    for i in range(1, 19):
        engine.load.get("整体升温").create("UTEMP", i, "X", 20.0)
    engine.load.create("正温度梯度", "TG", 1.0)
    for i in range(1, 19):
        engine.load.get("正温度梯度").create("GTEMP", i, "Z", "T", 2, 1.2, 0.0, 14.0, -0.1, 5.5, 0.679, -0.1, 5.5, -0.4, 0.0)
    engine.load.create("中横梁荷载工况", "CS", 1.0)
    engine.load.create("主梁单元自重", "CS", 1.0)
    engine.load.get("主梁单元自重").create("GRAVITY", 0.0, 0.0, -1.04)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_loadcases(engine)
