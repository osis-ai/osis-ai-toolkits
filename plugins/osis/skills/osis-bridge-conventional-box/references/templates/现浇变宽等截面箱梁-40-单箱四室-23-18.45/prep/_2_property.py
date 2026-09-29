"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束样条曲线_B1", "TENDON", [0.2, 0.0, -0.45, 0.0, 12.2, 0.0, -1.75, 10.0, 27.8, 0.0, -1.75, 10.0, 39.8, 0.0, -0.45, 0.0])
    engine.geometry.create_arc3d("钢束样条曲线_B2", "TENDON", [0.2, 0.0, -0.85, 0.0, 11.2, 0.0, -1.9, 10.0, 28.8, 0.0, -1.9, 10.0, 39.8, 0.0, -0.85, 0.0])
    engine.geometry.create_arc3d("钢束样条曲线_B3", "TENDON", [0.2, 0.0, -1.25, 0.0, 10.2, 0.0, -2.05, 10.0, 29.8, 0.0, -2.05, 10.0, 39.8, 0.0, -1.25, 0.0])
    engine.geometry.create_arc3d("钢束样条曲线_B4", "TENDON", [0.2, 0.0, -1.65, 0.0, 9.2, 0.0, -2.05, 10.0, 30.8, 0.0, -2.05, 10.0, 39.8, 0.0, -1.65, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
