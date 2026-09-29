"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.22, 0.0, -0.4, 0.0, 6.80172, 0.0, -1.325, 50.0, 18.1183, 0.0, -1.325, 50.0, 24.7, 0.0, -0.4, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.22, 0.0, -0.7, 0.0, 5.55653, 0.0, -1.45, 50.0, 19.3635, 0.0, -1.45, 50.0, 24.7, 0.0, -0.7, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.22, 0.0, -1.0, 0.0, 5.69076, 0.0, -1.575, 50.0, 19.2292, 0.0, -1.575, 50.0, 24.7, 0.0, -1.0, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.22, 0.0, -1.3, 0.0, 2.83645, 0.0, -1.575, 10.0, 22.0835, 0.0, -1.575, 10.0, 24.7, 0.0, -1.3, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
