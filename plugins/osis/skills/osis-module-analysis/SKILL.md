---
name: osis-module-analysis
description: 分析设置模块。生成 `prep/_9_analysis.py`,创建沉降组(支座不均匀沉降)和活载分析(车道 + 移动荷载体系 + 活载工况 + 横向折减 + 冲击系数)。当总控按依赖顺序加载到本模块时使用。沉降值由桥型层/项目层给定,活载参数由规范(默认 JTG D60-2015 公路-I 级)给定。
---

# osis-module-analysis

> 分析模块。负责沉降分析和活载分析,不修改主梁本身,只配置加载条件。

## 接到任务后,按顺序做

1. **从 `profile` 读取**:沉降值、活载等级、车道数、横向折减系数、横向分布系数、冲击系数参数。
2. **创建沉降组**(`settlement.group.create`),绑定节点 + 沉降值。
3. **创建沉降工况**(`settlement.create`),把沉降组 include 进去。
4. **创建移动荷载体系**(`live.grade.create_highway`)。
5. **创建车道线**(`live.lane.create_ve`),绑定到主梁单元组。
6. **创建活载工况**(`live.case.create`),配置横向折减 + 子工况 + 车道数。
7. **把沉降组、车道、活载工况名写入建模状态**,供 `_10` 引用。

## 沉降

```python
engine.settlement.group.create("桥墩1沉降组", 0.015, 64, 65)   # name, 沉降量(m), 节点 varargs(不是 list)
st = engine.settlement.create("沉降")
st.include("a", "桥墩1沉降组", "桥台1沉降组")                    # op 是第一个位置参数,必填
```

- 组名按位置命名(如 `桥墩1沉降组`),`_10` 按名引用。
- `include` 的 `op`:`"a"` 添加、`"r"` 移除;不传报 `TypeError`。`st.remove(...)` 等价于 `include("r", ...)`。
- 沉降值由桥型层/项目给定。

## 移动荷载体系与车道

```python
engine.live.grade.create_highway(name="移动荷载体系", code="JTGD60_2015", live_load_type="HIGHWAY_I")
engine.live.lane.create_ve(
    name="车道1", length=24.46, wheel=1.80, orientation=1,
    ref=0, ref_elems="主梁单元",   # ref=0 参照单元组时必填,必须等于 `_6` 建的组名
    offset_y=0.0, offset_z=0.0,
)
```

- `length` 在 docstring 里是"桥梁跨度"(m),取值由桥型层给定。
- 车道数、横向位置、是否设中载 + 左右偏载由桥型层 + 桥宽决定,本模块按方案创建。

## 活载工况

```python
lc = engine.live.case.create(name="车道荷载包络", code="JTGD60_2015", sub_cmb_type=1)   # 1=单独(包络) / 0=组合
lc.set_trans_reduction_factors(1.20, 1.00, 0.78, 0.67, 0.60, 0.55, 0.52, 0.50, 0.50, 0.50)   # varargs
lc.create_sub(
    sub_name="车道荷载工况1",
    grade_name="移动荷载体系",
    scalar=0.65,              # 横向分布系数
    calc_mu=True,
    bridge_type="CUSTOM",
    mu_params=[1.44],         # CUSTOM 时是结构基频(Hz)
    lane_names=["车道1", "车道2"],
)
lc.set_lane_count("车道荷载工况1", 0, 2)   # 不调则默认 0 ~ 最多车道数
```

- **横向折减系数**:第 k 个值对应加载 k 条车道(1 车道 1.20、2 车道 1.00 …),最多 10 个;个数要不少于实际车道数。
- **横向分布系数** = `create_sub` / `include` 的 `scalar`(命令流 `LiveAnalInc`),由桥型层按梁位给定。docstring 叫它"缩放系数"、默认 1.0,单梁模型不要沿用 1.0。
- **冲击系数**:`bridge_type` 决定 `mu_params` 的含义;`CUSTOM` 直接给基频,其余桥型的参数顺序用 `api_read live.case.create_sub` 查。

## 失败模式

- **`ref_elems` 组不存在** —— 车道引用组名与 `osis-module-element` 不一致
- **`车道荷载包络` 未在阶段激活** —— `_10` 漏了 `define_analysis(1, 'LIVE', '车道荷载包络')`
- **`Settlement.include` 漏 op** —— 必须传 `"a"` 或 `"r"`

(其他见 `osis-engine/references/error_diagnosis.md`)
