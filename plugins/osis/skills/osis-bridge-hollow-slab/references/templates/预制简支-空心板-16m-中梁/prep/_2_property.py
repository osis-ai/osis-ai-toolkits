"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.15, 0.0, -0.75, 0.0, 1.72307, 0.0, -0.86, 20.0, 14.2169, 0.0, -0.86, 20.0, 15.79, 0.0, -0.75, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.15, 0.0, -0.35, 0.0, 2.6755, 0.0, -0.75, 10.0, 13.2645, 0.0, -0.75, 10.0, 15.79, 0.0, -0.35, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
