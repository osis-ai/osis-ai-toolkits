"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.16, 0.0, -0.3, 0.0, 14.9612, 0.0, -1.335, 50.0, 19.9588, 0.0, -1.335, 50.0, 34.76, 0.0, -0.3, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.16, 0.0, -0.55, 0.0, 13.1736, 0.0, -1.46, 50.0, 21.7464, 0.0, -1.46, 50.0, 34.76, 0.0, -0.55, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.16, 0.0, -0.8, 0.0, 11.386, 0.0, -1.585, 50.0, 23.534, 0.0, -1.585, 50.0, 34.76, 0.0, -0.8, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.16, 0.0, -1.05, 0.0, 9.59844, 0.0, -1.71, 50.0, 25.3216, 0.0, -1.71, 50.0, 34.76, 0.0, -1.05, 0.0])
    engine.geometry.create_arc3d("钢束-5-N5", "TENDON", [0.16, 0.0, -1.585, 0.0, 3.73953, 0.0, -1.71, 30.0, 31.1805, 0.0, -1.71, 30.0, 34.76, 0.0, -1.585, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
