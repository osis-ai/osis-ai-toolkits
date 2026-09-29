"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.28, 0.0, -0.65, 0.0, 8.2669, 0.0, -1.915, 50.0, 26.6531, 0.0, -1.915, 50.0, 34.64, 0.0, -0.65, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.28, 0.0, -1.0, 0.0, 6.87787, 0.0, -2.045, 50.0, 28.0421, 0.0, -2.045, 50.0, 34.64, 0.0, -1.0, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.28, 0.0, -1.35, 0.0, 5.48884, 0.0, -2.175, 50.0, 29.4312, 0.0, -2.175, 50.0, 34.64, 0.0, -1.35, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.28, 0.0, -1.7, 0.0, 3.27903, 0.0, -2.175, 20.0, 31.641, 0.0, -2.175, 20.0, 34.64, 0.0, -1.7, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
