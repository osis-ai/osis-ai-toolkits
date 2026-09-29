"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.16, 0.0, -0.32, 0.0, 17.3248, 0.0, -1.43, 50.0, 22.5952, 0.0, -1.43, 50.0, 39.76, 0.0, -0.32, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.16, 0.0, -0.57, 0.0, 15.3919, 0.0, -1.555, 50.0, 24.5281, 0.0, -1.555, 50.0, 39.76, 0.0, -0.57, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.16, 0.0, -0.82, 0.0, 13.4589, 0.0, -1.68, 50.0, 26.4611, 0.0, -1.68, 50.0, 39.76, 0.0, -0.82, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.16, 0.0, -1.07, 0.0, 11.5259, 0.0, -1.805, 50.0, 28.3941, 0.0, -1.805, 50.0, 39.76, 0.0, -1.07, 0.0])
    engine.geometry.create_arc3d("钢束-5-N5", "TENDON", [0.16, 0.0, -1.32, 0.0, 9.59293, 0.0, -1.93, 50.0, 30.3271, 0.0, -1.93, 50.0, 39.76, 0.0, -1.32, 0.0])
    engine.geometry.create_arc3d("钢束-6-N6", "TENDON", [0.16, 0.0, -1.805, 0.0, 3.41384, 0.0, -1.93, 30.0, 36.5062, 0.0, -1.93, 30.0, 39.76, 0.0, -1.805, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
