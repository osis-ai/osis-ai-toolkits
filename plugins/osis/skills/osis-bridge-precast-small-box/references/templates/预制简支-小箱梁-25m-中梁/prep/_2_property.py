"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.16, 0.0, -0.25, 0.0, 8.50394, 0.0, -0.98, 30.0, 16.4161, 0.0, -0.98, 30.0, 24.76, 0.0, -0.25, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.16, 0.0, -0.5, 0.0, 6.90373, 0.0, -1.09, 30.0, 18.0163, 0.0, -1.09, 30.0, 24.76, 0.0, -0.5, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.16, 0.0, -0.75, 0.0, 5.30352, 0.0, -1.2, 30.0, 19.6165, 0.0, -1.2, 30.0, 24.76, 0.0, -0.75, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.16, 0.0, -1.0, 0.0, 3.70332, 0.0, -1.31, 30.0, 21.2167, 0.0, -1.31, 30.0, 24.76, 0.0, -1.0, 0.0])
    engine.geometry.create_arc3d("钢束-5-N5", "TENDON", [0.16, 0.0, -1.245, 0.0, 2.02136, 0.0, -1.31, 30.0, 22.8986, 0.0, -1.31, 30.0, 24.76, 0.0, -1.245, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
