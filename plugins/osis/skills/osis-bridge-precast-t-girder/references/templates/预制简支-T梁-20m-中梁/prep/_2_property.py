"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.22, 0.0, -0.42, 0.0, 6.92763, 0.0, -1.125, 40.0, 12.9924, 0.0, -1.125, 40.0, 19.7, 0.0, -0.42, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.22, 0.0, -0.67, 0.0, 5.73833, 0.0, -1.25, 40.0, 14.1817, 0.0, -1.25, 40.0, 19.7, 0.0, -0.67, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.22, 0.0, -0.92, 0.0, 4.54904, 0.0, -1.375, 40.0, 15.371, 0.0, -1.375, 40.0, 19.7, 0.0, -0.92, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.22, 0.0, -1.17, 0.0, 2.17044, 0.0, -1.375, 10.0, 17.7496, 0.0, -1.375, 10.0, 19.7, 0.0, -1.17, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
