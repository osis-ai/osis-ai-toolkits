"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.261, 0.0, -0.6, 0.0, 8.60896, 0.0, -1.625, 100.0, 21.311, 0.0, -1.625, 100.0, 29.659, 0.0, -0.6, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.261, 0.0, -0.9, 0.0, 7.18369, 0.0, -1.75, 100.0, 22.7363, 0.0, -1.75, 100.0, 29.659, 0.0, -0.9, 0.0])
    engine.geometry.create_arc3d("钢束-3-N3", "TENDON", [0.261, 0.0, -1.2, 0.0, 5.75843, 0.0, -1.875, 80.0, 24.1616, 0.0, -1.875, 80.0, 29.659, 0.0, -1.2, 0.0])
    engine.geometry.create_arc3d("钢束-4-N4", "TENDON", [0.261, 0.0, -1.5, 0.0, 2.92926, 0.0, -1.875, 20.0, 26.9907, 0.0, -1.875, 20.0, 29.659, 0.0, -1.5, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
