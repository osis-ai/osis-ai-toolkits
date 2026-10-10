---
name: osis-module-control
description: 控制参数模块。生成 `prep/_1_control.py`,设置控制参数(重力加速度、非线性选项、模态分析、收缩徐变/钢束计算开关)。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-control

> 控制参数模块。设置 OSIS 计算过程的全局开关和物理参数。

## 接到任务后,按顺序做

1. **从 `profile` 读取**:重力加速度、是否考虑收缩/徐变/松弛、是否非线性分析、模态分析选项。
2. **设置控制参数**(`engine.control.set_*`)。
3. **记录到建模状态**(`osis-engine` §维护建模状态 的 `profile` 字段)。

## `engine.clear()` 放置规则(铁律)

`engine.clear()` + `engine.clc()` **只允许出现在 `main.py` 的全量入口里,禁止写进 `_1_control.py` 或任何 `_N` 模块**。

- `setup_control()` 只设参数;`main.py` 在调 `setup_control` 之前显式 `engine.clear()`。
- 单跑 `_1_control.py` 只改开关、不清模型;写回怎么选见 `osis-engine` §写回。

## 公共约定

`set_*` 启用类开关的 `enabled` 参数都是 `Literal[0, 1]`(`0`=关、`1`=开);传 `True/False` 会被强制转为 0/1。位置参数不固定,推荐用关键字调用。

## 常用控制参数

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
engine.control.set_nonlinear(geom=0, link=0)            # 不开非线性
engine.control.set_line_search(0)                       # 不开线性搜索
engine.control.set_auto_time_step(0)                    # 不开自动时间步
engine.control.set_substitution_steps(nls, nsbmx)       # 荷载步数 + 最大子步数
engine.control.set_modal_opt(0)                         # 模态分析特征值数(0=不开)
```

## 默认值与必设建议

大部分参数不调时使用默认值即可。常见必设:

- `set_gravity_acceleration(9.8066)` —— 必设,除非桥型层明确覆盖
- `set_calc_tendon(1)` —— 任何含预应力的桥型必设
- `set_calc_creep(1)` / `set_calc_shrink(1)` —— 任何施工阶段分析必设

其他参数按需开启。

## 失败模式

- **`enabled` 传 `True/False`** —— 字面量只接受 `0/1`,布尔会被强转可能产生预期外结果
- 未启用钢束计算 / 收缩徐变 —— 预应力、长期效应不生效

(其他见 `osis-engine/references/error_diagnosis.md`)

