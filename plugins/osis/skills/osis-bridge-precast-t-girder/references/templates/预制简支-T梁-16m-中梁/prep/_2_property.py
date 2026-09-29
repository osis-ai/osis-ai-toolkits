"""OSIS 命令流 PROPERTY 模块 — 几何属性(坐标系、收缩徐变特性、钢束线型等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_property(engine: OSISEngine) -> None:
    # 创建样条曲线（便捷入口，内部转发到对应 create_* 方法）
    engine.geometry.create_arc3d("钢束-1-N1", "TENDON", [0.144, 0.0, -0.25, 0.0, 6.00727, 0.0, -0.66, 20.0, 9.91273, 0.0, -0.66, 20.0, 15.776, 0.0, -0.25, 0.0])
    engine.geometry.create_arc3d("钢束-2-N2", "TENDON", [0.144, 0.0, -0.55, 0.0, 5.02114, 0.0, -0.78, 20.0, 10.8989, 0.0, -0.78, 20.0, 15.776, 0.0, -0.55, 0.0])

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_property(engine)
