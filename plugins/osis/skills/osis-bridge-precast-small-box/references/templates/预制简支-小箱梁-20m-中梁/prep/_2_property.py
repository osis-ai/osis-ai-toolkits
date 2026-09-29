"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.16, 0.0, -0.3, 0.0, 6.90373, 0.0, -0.89, 30.0, 13.0163, 0.0, -0.89, 30.0, 19.76, 0.0, -0.3, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.16, 0.0, -0.55, 0.0, 5.30352, 0.0, -1.0, 30.0, 14.6165, 0.0, -1.0, 30.0, 19.76, 0.0, -0.55, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.16, 0.0, -0.8, 0.0, 3.70332, 0.0, -1.11, 30.0, 16.2167, 0.0, -1.11, 30.0, 19.76, 0.0, -0.8, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.16, 0.0, -1.045, 0.0, 2.02136, 0.0, -1.11, 30.0, 17.8986, 0.0, -1.11, 30.0, 19.76, 0.0, -1.045, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
