"""OSIS 命令流 SECTION 模块 — 截面定义(标准截面 + 加厚/变化截面)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_sections(engine: OSISEngine) -> None:
    # 创建截面（便捷入口，内部转发到对应 create_* 方法）
    engine.section.create(1, "标准截面", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.6, 0.2, 0.6, 0.2, 0.25, 0, 0.0, 0.0, 0.05)
    # 设置截面偏移。
    engine.section.get(1).set_offset("Middle", 0.0607, "Top", 0.0)
    # 设置截面网格。
    engine.section.get(1).set_mesh(0, 0.1)
    engine.section.create(2, "墩顶截面", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5, 0.4, 0.6, 0.9, 0.1, 0, 0.0, 0.0, 0.05)
    engine.section.get(2).set_offset("Middle", 0.0405, "Top", 0.0)
    engine.section.get(2).set_mesh(0, 0.1)
    engine.section.create(3, "加厚截面", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5, 0.4, 0.6, 0.9, 0.1, 0, 0.0, 0.0, 0.05)
    engine.section.get(3).set_offset("Middle", 0.0405, "Top", 0.0)
    engine.section.get(3).set_mesh(0, 0.1)
    engine.section.create(5, "截面1", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5865, 0.2269, 0.6, 0.2942, 0.2298, 0, 0.0, 0.0, 0.05)
    engine.section.get(5).set_offset("Middle", 0.0562, "Top", 0.0)
    engine.section.get(5).set_mesh(0, 0.1)
    engine.section.create(6, "截面2", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5731, 0.2538, 0.6, 0.3883, 0.2096, 0, 0.0, 0.0, 0.05)
    engine.section.get(6).set_offset("Middle", 0.0524, "Top", 0.0)
    engine.section.get(6).set_mesh(0, 0.1)
    engine.section.create(7, "截面3", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.55, 0.3, 0.6, 0.55, 0.175, 0, 0.0, 0.0, 0.05)
    engine.section.get(7).set_offset("Middle", 0.0475, "Top", 0.0)
    engine.section.get(7).set_mesh(0, 0.1)
    engine.section.create(8, "截面4", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5269, 0.3462, 0.6, 0.7117, 0.1404, 0, 0.0, 0.0, 0.05)
    engine.section.get(8).set_offset("Middle", 0.0437, "Top", 0.0)
    engine.section.get(8).set_mesh(0, 0.1)
    engine.section.create(9, "截面5", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5135, 0.3731, 0.6, 0.8058, 0.1202, 0, 0.0, 0.0, 0.05)
    engine.section.get(9).set_offset("Middle", 0.042, "Top", 0.0)
    engine.section.get(9).set_mesh(0, 0.1)
    engine.section.create(10, "截面6", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5135, 0.3731, 0.6, 0.8058, 0.1202, 0, 0.0, 0.0, 0.05)
    engine.section.get(10).set_offset("Middle", 0.042, "Top", 0.0)
    engine.section.get(10).set_mesh(0, 0.1)
    engine.section.create(11, "截面7", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5269, 0.3462, 0.6, 0.7117, 0.1404, 0, 0.0, 0.0, 0.05)
    engine.section.get(11).set_offset("Middle", 0.0437, "Top", 0.0)
    engine.section.get(11).set_mesh(0, 0.1)
    engine.section.create(12, "截面8", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.55, 0.3, 0.6, 0.55, 0.175, 0, 0.0, 0.0, 0.05)
    engine.section.get(12).set_offset("Middle", 0.0475, "Top", 0.0)
    engine.section.get(12).set_mesh(0, 0.1)
    engine.section.create(13, "截面9", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5731, 0.2538, 0.6, 0.3883, 0.2096, 0, 0.0, 0.0, 0.05)
    engine.section.get(13).set_offset("Middle", 0.0524, "Top", 0.0)
    engine.section.get(13).set_mesh(0, 0.1)
    engine.section.create(14, "截面10", "TGIRDER", "Left", 2.5, 1.18, 0.875, 0.0, 0.2, 0.25, 0.5865, 0.2269, 0.6, 0.2942, 0.2298, 0, 0.0, 0.0, 0.05)
    engine.section.get(14).set_offset("Middle", 0.0562, "Top", 0.0)
    engine.section.get(14).set_mesh(0, 0.1)
    # 添加或修改抗剪钢筋（按类型分发）
    engine.section.get(1).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(2).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(3).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(5).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(6).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(7).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(8).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(9).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(10).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(11).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(12).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(13).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)
    engine.section.get(14).add_rebar_s("ShearStirrup", 2, 0.1, 0.000226195)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_sections(engine)
