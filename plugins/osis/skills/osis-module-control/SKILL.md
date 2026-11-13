---
name: osis-module-control
description: 控制参数模块。生成 `prep/_1_control.py`,设置控制参数(重力加速度、非线性选项、模态分析、收缩徐变/钢束计算开关)。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-control

> `prep/_1_control.py`:`setup_control(engine)` 设置计算的全局开关。

## 写法

```python
engine.control.set_gravity_acceleration(9.8066)        # 重力加速度(m/s²)
engine.control.set_calc_tendon(1)                       # 计算预应力
engine.control.set_calc_creep(1)                        # 计算徐变
engine.control.set_calc_shrink(1)                       # 计算收缩
engine.control.set_calc_shear(1)                        # 计算剪切
engine.control.set_calc_concurrent_force(1)             # 计算并发反力
engine.control.set_calc_relaxation(1)                   # 计算钢束松弛
engine.control.set_inc_tendon(1)                        # 钢束自重及几何影响
engine.control.set_mod_loc_coor(0)                      # 不修改变截面单元局部坐标
engine.control.set_nonlinear(geom=0)                    # 不开非线性
engine.control.set_line_search(0)                       # 不开线性搜索
engine.control.set_auto_time_step(0)                    # 不开自动时间步
engine.control.set_substitution_steps(nls, nsbmx)       # 荷载步数 + 最大子步数
engine.control.set_modal_opt(0)                         # 模态分析特征值数(0=不开)
```

- 开关类参数传 `0` / `1`,不要传 `True` / `False`。
- 必设:`set_gravity_acceleration`;含预应力必开 `set_calc_tendon`;有施工阶段必开 `set_calc_creep` / `set_calc_shrink`,漏开时预应力、长期效应不生效。其余按需。
- **`engine.clear()` / `engine.clc()` 只写在 `main.py` 入口,不写进 `_1_control.py` 或任何 `_N` 模块**:单跑 `_1` 应该只改开关、不清模型。
