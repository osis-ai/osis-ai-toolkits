"""OSIS 命令流 ELEMENT 模块 — 单元(梁/弹簧)创建 + 分组"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_elements(engine: OSISEngine) -> None:
    # 创建单元（便捷入口，内部转发到对应 create_* 方法）
    engine.element.create(1, "BEAM3D", 1, 2, 1, 4, 4, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(2, "BEAM3D", 2, 3, 1, 4, 4, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(3, "BEAM3D", 3, 4, 1, 5, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(4, "BEAM3D", 4, 5, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(5, "BEAM3D", 5, 6, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(6, "BEAM3D", 6, 7, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(7, "BEAM3D", 7, 8, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(8, "BEAM3D", 8, 9, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(9, "BEAM3D", 9, 10, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(10, "BEAM3D", 10, 11, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(11, "BEAM3D", 11, 12, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(12, "BEAM3D", 12, 13, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(13, "BEAM3D", 13, 14, 1, 1, 1, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(14, "BEAM3D", 14, 15, 1, 1, 5, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(15, "BEAM3D", 15, 16, 1, 4, 4, 1, 1, 0.0, 0, 0.0, 0)
    engine.element.create(16, "BEAM3D", 16, 17, 1, 4, 4, 1, 1, 0.0, 0, 0.0, 0)
    # 分配或重置单个单元的理论厚度
    engine.prop.assign_component_thickness(0.3033, "a", "1to2", "15to16")
    engine.prop.assign_component_thickness(0.2725, "a", 3, 14)
    engine.prop.assign_component_thickness(0.2418, "a", "4to13")
    # 创建单元组
    engine.element.group.create("钢束-1-N1线型单元", "c")
    engine.element.group.create("钢束-1-N1线型单元", "a", "1to16")
    engine.element.group.create("钢束-2-N2线型单元", "c")
    engine.element.group.create("钢束-2-N2线型单元", "a", "1to16")
    engine.element.group.create("钢束-3-N3线型单元", "c")
    engine.element.group.create("钢束-3-N3线型单元", "a", "1to16")
    engine.element.group.create("钢束-4-N4线型单元", "c")
    engine.element.group.create("钢束-4-N4线型单元", "a", "1to16")
    engine.element.group.create("钢束-5-N5线型单元", "c")
    engine.element.group.create("钢束-5-N5线型单元", "a", "1to16")
    engine.element.group.create("主梁单元", "c")
    engine.element.group.create("主梁单元", "a", "1to16")

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_elements(engine)
