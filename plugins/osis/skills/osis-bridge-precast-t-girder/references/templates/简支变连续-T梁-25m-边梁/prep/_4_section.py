"""OSIS 命令流 SECTION 模块 — 截面定义(标准截面 + 加厚/变化截面)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_sections(engine: OSISEngine) -> None:
    # 创建截面（便捷入口，内部转发到对应 create_* 方法）
    engine.section.create(1, "标准截面", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.6, 0.2, 0.6, 0.2, 0.2, 0, 0.0, 0.0, 0.05)
    # 设置截面偏移。
    engine.section.get(1).set_offset("Middle", 0.0444, "Top", 0.0)
    # 设置截面网格。
    engine.section.get(1).set_mesh(0, 0.1)
    engine.section.create(2, "墩顶截面", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.5, 0.4, 0.6, 0.7, 0.1, 0, 0.0, 0.0, 0.05)
    engine.section.get(2).set_offset("Middle", 0.0317, "Top", 0.0)
    engine.section.get(2).set_mesh(0, 0.1)
    engine.section.create(3, "加厚截面", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.5, 0.4, 0.6, 0.7, 0.1, 0, 0.0, 0.0, 0.05)
    engine.section.get(3).set_offset("Middle", 0.0317, "Top", 0.0)
    engine.section.get(3).set_mesh(0, 0.1)
    engine.section.create(5, "截面1", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.55, 0.3, 0.6, 0.45, 0.15, 0, 0.0, 0.0, 0.05)
    engine.section.get(5).set_offset("Middle", 0.0361, "Top", 0.0)
    engine.section.get(5).set_mesh(0, 0.1)
    engine.section.create(6, "截面2", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.55, 0.3, 0.6, 0.45, 0.15, 0, 0.0, 0.0, 0.05)
    engine.section.get(6).set_offset("Middle", 0.0361, "Top", 0.0)
    engine.section.get(6).set_mesh(0, 0.1)
    engine.section.create(7, "截面3", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.55, 0.3, 0.6, 0.45, 0.15, 0, 0.0, 0.0, 0.05)
    engine.section.get(7).set_offset("Middle", 0.0361, "Top", 0.0)
    engine.section.get(7).set_mesh(0, 0.1)
    engine.section.create(8, "截面4", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.55, 0.3, 0.6, 0.45, 0.15, 0, 0.0, 0.0, 0.05)
    engine.section.get(8).set_offset("Middle", 0.0361, "Top", 0.0)
    engine.section.get(8).set_mesh(0, 0.1)
    engine.section.create(9, "截面5", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.55, 0.3, 0.6, 0.45, 0.15, 0, 0.0, 0.0, 0.05)
    engine.section.get(9).set_offset("Middle", 0.0361, "Top", 0.0)
    engine.section.get(9).set_mesh(0, 0.1)
    engine.section.create(10, "截面6", "TGIRDER", "Left", 1.7, 1.0, 0.8, 0.0, 0.2, 0.25, 0.55, 0.3, 0.6, 0.45, 0.15, 0, 0.0, 0.0, 0.05)
    engine.section.get(10).set_offset("Middle", 0.0361, "Top", 0.0)
    engine.section.get(10).set_mesh(0, 0.1)
    # 添加或修改纵向钢筋（按输入方式分发）
    engine.section.get(1).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(1).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.04, 18, 0.1, "D12")
    # 添加或修改抗剪钢筋（按类型分发）
    engine.section.get(1).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(2).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(2).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.045, 16, 0.11, "D20")
    engine.section.get(2).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(3).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(3).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.04, 18, 0.1, "D12")
    engine.section.get(3).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(5).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(5).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.04, 18, 0.1, "D12")
    engine.section.get(5).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(6).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(6).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.04, 18, 0.1, "D12")
    engine.section.get(6).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(7).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(7).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.04, 18, 0.1, "D12")
    engine.section.get(7).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(8).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(8).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.04, 18, 0.1, "D12")
    engine.section.get(8).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(9).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(9).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.04, 18, 0.1, "D12")
    engine.section.get(9).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(10).add_rebar_l(1, "LineA", 2, "Center", 0.0444, "Bottom", 0.045, 6, 0.1, "D25")
    engine.section.get(10).add_rebar_l(2, "LineA", 2, "Center", -0.06, "Top", -0.04, 18, 0.1, "D12")
    engine.section.get(10).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_sections(engine)
