"""OSIS 命令流 SECTION 模块 — 截面定义(标准截面 + 加厚/变化截面)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_sections(engine: OSISEngine) -> None:
    # 创建截面（便捷入口，内部转发到对应 create_* 方法）
    engine.section.create(1, "12.75_", "CONVENTIONALBOX", 2.2, 6.375, 6.375, 4.375, 4.375, 0.5, 0.25, 0.22, 0.5, 0.5, 2, 3.625, 3.625, 3.625, 3.625, 0.0, 0.45, 0.8, 0.45, 0.8, 0.45, 0.6, 0.2, 0.6, 0.2, 0.8, 0.45, 0.6, 0.2, 2.0, 0.15, 0.0, 0.45, 0.45, 1, 2.0, 0.15, 0.0, 0.45, 0.45, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    # 设置截面偏移。
    engine.section.get(1).set_offset("Middle", 0.0, "Top", 0.0)
    # 设置截面网格。
    engine.section.get(1).set_mesh(0, 0.1)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_sections(engine)
