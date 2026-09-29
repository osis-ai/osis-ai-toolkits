"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.301, 0.0, -0.55, 0.0, 12.0289, 0.0, -1.99, 100.0, 27.8911, 0.0, -1.99, 100.0, 39.619, 0.0, -0.55, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.301, 0.0, -0.85, 0.0, 10.6443, 0.0, -2.12, 100.0, 29.2757, 0.0, -2.12, 100.0, 39.619, 0.0, -0.85, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.301, 0.0, -1.15, 0.0, 9.25978, 0.0, -2.25, 100.0, 30.6602, 0.0, -2.25, 100.0, 39.619, 0.0, -1.15, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.301, 0.0, -1.45, 0.0, 7.83452, 0.0, -2.375, 100.0, 32.0855, 0.0, -2.375, 100.0, 39.619, 0.0, -1.45, 0.0])
    engine.geometry.create_arc3d("钢束-5-N5", "TENDON", [0.301, 0.0, -1.8, 0.0, 5.34771, 0.0, -2.375, 50.0, 34.5723, 0.0, -2.375, 50.0, 39.619, 0.0, -1.8, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
