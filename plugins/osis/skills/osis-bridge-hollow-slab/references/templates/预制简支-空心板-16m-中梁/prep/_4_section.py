"""OSIS 命令流 SECTION 模块 — 截面定义(标准截面 + 加厚/变化截面)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_sections(engine: OSISEngine) -> None:
    # 创建截面（便捷入口，内部转发到对应 create_* 方法）
    engine.section.create(1, "标准截面", "HOLLOWSLAB", "Middle", 0.95, 1.0, 0.57, 0.05, 0.12, 0.12, 0.16, 0.12, 0.24, 0.38, 0.15, 0.08, 0.12, 0.08, 0.05, 0.05, 0.08, 0.08, 0.12)
    # 设置截面偏移。
    engine.section.get(1).set_offset("Middle", 0.0, "Top", 0.0)
    # 设置截面网格。
    engine.section.get(1).set_mesh(0, 0.1)
    engine.section.create(2, "墩顶截面", "HOLLOWSLAB", "Middle", 0.95, 1.0, 0.62, 0.0, 0.12, 0.25, 0.32, 0.12, 0.24, 0.38, 0.15, 0.08, 0.12, 0.08, 0.0, 0.05, 0.0, 0.08, 0.12)
    engine.section.get(2).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(2).set_mesh(0, 0.1)
    engine.section.create(3, "加厚截面", "HOLLOWSLAB", "Middle", 0.95, 1.0, 0.57, 0.05, 0.12, 0.25, 0.24, 0.12, 0.24, 0.38, 0.15, 0.08, 0.12, 0.08, 0.05, 0.05, 0.08, 0.08, 0.12)
    engine.section.get(3).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(3).set_mesh(0, 0.1)
    # 添加或修改抗剪钢筋（按类型分发）
    engine.section.get(1).add_rebar_s("ShearStirrup", 2, 0.15, 7.85398e-05)
    engine.section.get(2).add_rebar_s("ShearStirrup", 2, 0.15, 7.85398e-05)
    engine.section.get(3).add_rebar_s("ShearStirrup", 2, 0.15, 7.85398e-05)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_sections(engine)
