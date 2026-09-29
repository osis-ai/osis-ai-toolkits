"""OSIS 命令流 SECTION 模块 — 截面定义(标准截面 + 加厚/变化截面)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_sections(engine: OSISEngine) -> None:
    # 定义矩阵（用于自定义截面等）
    engine.matrix("ContourPointsMatrix", [[1, -4.375, -2.0], [1, 0.0, -2.0], [1, 4.375, -2.0], [1, 4.375, -0.45], [1, 6.375, -0.15], [1, 6.375, 0.0], [1, 0.0, -0.0], [1, -6.375, 0.0], [1, -6.375, -0.15], [1, -4.375, -0.45], [2, -3.275, -1.78], [2, -0.85, -1.78], [2, -0.25, -1.58], [2, -0.25, -0.45], [2, -1.05, -0.25], [2, -3.075, -0.25], [2, -3.875, -0.45], [2, -3.875, -1.58], [3, 0.85, -1.78], [3, 3.275, -1.78], [3, 3.875, -1.58], [3, 3.875, -0.45], [3, 3.075, -0.25], [3, 1.05, -0.25], [3, 0.25, -0.45], [3, 0.25, -1.58]])
    # 创建截面（便捷入口，内部转发到对应 create_* 方法）
    engine.section.create(1, "12.75_", "CUSTOM", "ContourPointsMatrix")
    # 设置截面偏移。
    engine.section.get(1).set_offset("Middle", 0.0, "Top", 0.0)
    # 设置截面网格。
    engine.section.get(1).set_mesh(0, 0.1)
    engine.section.create(2, "16.75_", "CONVENTIONALBOX", 2.0, 8.375, 8.375, 6.375, 6.375, 0.5, 0.25, 0.22, 0.5, 0.5, 3, 3.5833, 3.5834, 3.5833, 3.5833, 0.0, 0.45, 0.8, 0.45, 0.8, 0.45, 0.6, 0.2, 0.6, 0.2, 0.8, 0.45, 0.6, 0.2, 2.0, 0.15, 0.0, 0.45, 0.45, 1, 2.0, 0.15, 0.0, 0.45, 0.45, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(2).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(2).set_mesh(0, 0.1)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_sections(engine)
