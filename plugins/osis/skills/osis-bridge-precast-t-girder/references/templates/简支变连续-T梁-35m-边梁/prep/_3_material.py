"""OSIS 命令流 MATERIAL 模块 — 材料定义(混凝土、钢筋、钢绞线)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def build_materials(engine: OSISEngine) -> None:
    # 创建或修改收缩徐变特性
    engine.prop.creep_shrink.create(1, "收缩徐变", fcuk=50e6, avg_humidity=75.0, type_coeff=5.0, birth_by_shrinking=3)
    # 创建材料（便捷入口，内部转发到对应 create_* 方法）
    engine.material.create(1, "C50", "CONC", "JTG3362_2018", "C50", 1, 0.05)
    engine.material.create(2, "HRB400", "REBAR", "JTG3362_2018", "HRB400", 0.02)
    engine.material.create(3, "Strand1860", "PRESTRESSED", "JTG3362_2018", "Strand1860", 0.02)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        build_materials(engine)
