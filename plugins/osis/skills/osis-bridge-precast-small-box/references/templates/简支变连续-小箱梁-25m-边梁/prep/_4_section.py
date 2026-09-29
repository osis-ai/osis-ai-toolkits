"""OSIS 命令流 SECTION 模块 — 截面定义(标准截面 + 加厚/变化截面)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_sections(engine: OSISEngine) -> None:
    # 创建截面（便捷入口，内部转发到对应 create_* 方法）
    engine.section.create(1, "标准截面", "SMALLBOX", "Left", 1.4, 1.65, 1.2, 0.0, 1.0, 0.18, 0.18, 0.18, 3.5, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    # 设置截面偏移。
    engine.section.get(1).set_offset("Middle", 0.1253, "Top", 0.0)
    # 设置截面网格。
    engine.section.get(1).set_mesh(0, 0.1)
    engine.section.create(2, "墩顶截面", "SMALLBOX", "Left", 1.4, 1.65, 1.2, 0.0, 1.0, 0.18, 0.3, 0.3, 3.5, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(2).set_offset("Middle", 0.0979, "Top", 0.0)
    engine.section.get(2).set_mesh(0, 0.1)
    engine.section.create(3, "加厚截面", "SMALLBOX", "Left", 1.4, 1.65, 1.2, 0.0, 1.0, 0.18, 0.3, 0.3, 3.5, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(3).set_offset("Middle", 0.0979, "Top", 0.0)
    engine.section.get(3).set_mesh(0, 0.1)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_sections(engine)
