"""OSIS 命令流 CONTROL 模块 — 全局控制参数(重力、非线性、收缩徐变开关等)"""

from __future__ import annotations

from pyosis import batch

from pyosis.core.engine import OSISEngine

def setup_control(engine: OSISEngine) -> None:
    # 设置整体坐标系下三个方向的重力加速度分量
    engine.control.set_gravity_acceleration(9.8066)
    # 设置是否计算预应力效应
    engine.control.set_calc_tendon(1)
    # 设置是否计算并发反力
    engine.control.set_calc_concurrent_force(1)
    # 设置是否计算收缩
    engine.control.set_calc_shrink(1)
    # 设置是否计算徐变
    engine.control.set_calc_creep(1)
    # 设置是否计算剪切变形
    engine.control.set_calc_shear(1)
    # 设置是否计算钢束松弛
    engine.control.set_calc_relaxation(1)
    # 设置是否修改变截面单元局部坐标轴以计算内力/应力
    engine.control.set_mod_loc_coor(0)
    # 设置是否考虑钢束自重及钢束对截面几何特性的影响
    engine.control.set_inc_tendon(1)
    # 设置非线性分析控制开关
    engine.control.set_nonlinear(0, 0)
    # 设置求解阶段的线性搜索开关
    engine.control.set_line_search(0)
    # 设置是否启用自动计算时间荷载步
    engine.control.set_auto_time_step(0)
    # 指定荷载步数与最大荷载子步数
    engine.control.set_substitution_steps(1, 20)
    # 定义模态分析所需的特征值最大数目。
    engine.dynamic.modal.set_modal_opt(0)

if __name__ == "__main__":
    from _0_engine import engine
    with batch():
        setup_control(engine)
