"""OSIS 命令流 SECTION 模块 — 截面定义(标准截面 + 加厚/变化截面)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_sections(engine: OSISEngine) -> None:
    # 创建截面（便捷入口，内部转发到对应 create_* 方法）
    engine.section.create(1, "跨中截面", "CONVENTIONALBOX", 2.4, 6.375, 6.375, 3.5, 3.5, 0.5, 0.28, 0.32, 0.5, 0.5, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    # 设置截面偏移。
    engine.section.get(1).set_offset("Middle", 0.0, "Top", 0.0)
    # 设置截面网格。
    engine.section.get(1).set_mesh(0, 0.1)
    engine.section.create(2, "桥墩", "RECT", "Chamfer", "Solid", 7.0, 2.5, 1.0, 0.5, 0.0, 1.0, 1.0, 0.5, 0.25, 0, 1.0, 0.5, 0.25, 1, 1.2, 0.8, 0.2)
    engine.section.get(2).set_offset("Middle", 0.0, "Center", 0.0)
    engine.section.get(2).set_mesh(0, 0.1)
    engine.section.create(3, "边跨现浇段截面1", "CONVENTIONALBOX", 2.4, 6.375, 6.375, 3.5, 3.5, 0.75, 0.5, 0.5, 0.75, 0.75, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.92, 1.5, 0.92, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(3).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(3).set_mesh(0, 0.1)
    engine.section.create(4, "1号墩悬浇段截面1", "CONVENTIONALBOX", 2.429632, 6.375, 6.375, 3.5, 3.5, 0.5, 0.28, 0.346752, 0.5, 0.5, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(4).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(4).set_mesh(0, 0.1)
    engine.section.create(5, "1号墩悬浇段截面2", "CONVENTIONALBOX", 2.536184, 6.375, 6.375, 3.5, 3.5, 0.5, 0.28, 0.38242, 0.5, 0.5, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(5).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(5).set_mesh(0, 0.1)
    engine.section.create(6, "1号墩悬浇段截面3", "CONVENTIONALBOX", 2.682547, 6.375, 6.375, 3.5, 3.5, 0.5, 0.28, 0.413631, 0.5, 0.5, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(6).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(6).set_mesh(0, 0.1)
    engine.section.create(7, "1号墩悬浇段截面4", "CONVENTIONALBOX", 2.87422, 6.375, 6.375, 3.5, 3.5, 0.625, 0.28, 0.444841, 0.625, 0.625, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(7).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(7).set_mesh(0, 0.1)
    engine.section.create(8, "1号墩悬浇段截面5", "CONVENTIONALBOX", 3.108627, 6.375, 6.375, 3.5, 3.5, 0.75, 0.28, 0.476051, 0.75, 0.75, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(8).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(8).set_mesh(0, 0.1)
    engine.section.create(9, "1号墩悬浇段截面6", "CONVENTIONALBOX", 3.383884, 6.375, 6.375, 3.5, 3.5, 0.75, 0.28, 0.507261, 0.75, 0.75, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(9).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(9).set_mesh(0, 0.1)
    engine.section.create(10, "1号墩悬浇段截面7", "CONVENTIONALBOX", 3.698519, 6.375, 6.375, 3.5, 3.5, 0.75, 0.28, 0.538471, 0.75, 0.75, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(10).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(10).set_mesh(0, 0.1)
    engine.section.create(11, "1号墩悬浇段截面8", "CONVENTIONALBOX", 4.104787, 6.375, 6.375, 3.5, 3.5, 0.75, 0.28, 0.57414, 0.75, 0.75, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(11).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(11).set_mesh(0, 0.1)
    engine.section.create(12, "1号墩零号段截面9", "CONVENTIONALBOX", 4.429657, 6.375, 6.375, 3.5, 3.5, 0.75, 0.28, 0.6, 0.75, 0.75, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.7, 1.5, 0.7, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(12).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(12).set_mesh(0, 0.1)
    engine.section.create(13, "1号墩零号段截面10", "CONVENTIONALBOX", 4.5, 6.375, 6.375, 3.5, 3.5, 1.0, 0.5, 0.7, 1.0, 1.0, 1, 5.05, 4.5, 5.05, 5.05, 0.0, 0.92, 1.5, 0.92, 1.0, 0.5, 0.5, 0.35, 0.6, 0.3, 1.0, 0.5, 0.6, 0.3, 2.875, 0.2, 1.325, 0.7, 0.4, 1, 2.875, 0.2, 1.325, 0.7, 0.4, "Integral", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    engine.section.get(13).set_offset("Middle", 0.0, "Top", 0.0)
    engine.section.get(13).set_mesh(0, 0.1)
    # 添加或修改抗剪钢筋（按类型分发）
    engine.section.get(1).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(1).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(3).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(3).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(4).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(4).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(5).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(5).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(6).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(6).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(7).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(7).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(8).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(8).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(9).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(9).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(10).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(10).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(11).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(11).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(12).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(12).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)
    engine.section.get(13).add_rebar_s("ShearStirrup", 3, 0.1, 0.000615752)
    engine.section.get(13).add_rebar_s("WebVerticalRebar", 4, 0.5, 0.00241274, 90.0, 567400.0, 0.8)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_sections(engine)
