"""OSIS 命令流 SECTION 模块 — 截面定义(标准截面 + 加厚/变化截面)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_sections(engine: OSISEngine) -> None:
    # 创建截面（便捷入口，内部转发到对应 create_* 方法）
    engine.section.create(1, "标准截面", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.18, 0.2, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    # 设置截面偏移。
    engine.section.get(1).set_offset("Middle", 0.1053, "Top", 0.0)
    # 设置截面网格。
    engine.section.get(1).set_mesh(0, 0.1)
    engine.section.create(2, "墩顶截面", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.36, 0.32, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(2).set_offset("Middle", 0.0792, "Top", 0.0)
    engine.section.get(2).set_mesh(0, 0.1)
    engine.section.create(3, "加厚截面", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.36, 0.32, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(3).set_offset("Middle", 0.0792, "Top", 0.0)
    engine.section.get(3).set_mesh(0, 0.1)
    engine.section.create(5, "截面1", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.27, 0.26, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(5).set_offset("Middle", 0.0899, "Top", 0.0)
    engine.section.get(5).set_mesh(0, 0.1)
    engine.section.create(6, "截面2", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.27, 0.26, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(6).set_offset("Middle", 0.0899, "Top", 0.0)
    engine.section.get(6).set_mesh(0, 0.1)
    engine.section.create(7, "截面3", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.27, 0.26, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(7).set_offset("Middle", 0.0899, "Top", 0.0)
    engine.section.get(7).set_mesh(0, 0.1)
    engine.section.create(8, "截面4", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.27, 0.26, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(8).set_offset("Middle", 0.0899, "Top", 0.0)
    engine.section.get(8).set_mesh(0, 0.1)
    engine.section.create(9, "截面5", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.27, 0.26, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(9).set_offset("Middle", 0.0899, "Top", 0.0)
    engine.section.get(9).set_mesh(0, 0.1)
    engine.section.create(10, "截面6", "SMALLBOX", "Left", 1.8, 1.65, 1.2, 0.0, 1.0, 0.18, 0.27, 0.26, 4.0, 0.18, 0.25, 0.2, 0.15, 0.25, 0.05, 0.05, 0, 0.0, 0.0, 0.05)
    engine.section.get(10).set_offset("Middle", 0.0899, "Top", 0.0)
    engine.section.get(10).set_mesh(0, 0.1)
    # 添加或修改抗剪钢筋（按类型分发）
    engine.section.get(1).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)
    engine.section.get(2).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)
    engine.section.get(3).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)
    engine.section.get(5).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)
    engine.section.get(6).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)
    engine.section.get(7).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)
    engine.section.get(8).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)
    engine.section.get(9).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)
    engine.section.get(10).add_rebar_s("ShearStirrup", 2, 0.1, 0.000452389)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_sections(engine)
