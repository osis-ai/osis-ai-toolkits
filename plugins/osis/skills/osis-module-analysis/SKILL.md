---
name: osis-module-analysis
description: 分析设置模块。生成 `prep/_9_analysis.py`,创建沉降组(支座不均匀沉降)和活载分析(车道 + 移动荷载体系 + 活载工况 + 横向折减 + 冲击系数)。当总控按依赖顺序加载到本模块时使用。沉降值由桥型层/项目层给定,活载参数由规范(默认 JTG D60-2015 公路-I 级)给定。
---

# osis-module-analysis

> 分析模块。负责沉降分析和活载分析,所有这些都不修改主梁本身,只配置加载条件。

## 接到任务后,按顺序做

1. **从 `profile` 读取**:沉降值、活载等级、车道数、横向折减系数、冲击系数。
2. **创建沉降组**(`settlement.group.create`),绑定节点 + 沉降值。
3. **创建沉降工况**(`settlement.create`),把沉降组 include 进去。
4. **创建移动荷载体系**(`live.grade.create_highway`)。
5. **创建车道线**(`live.lane.create_ve`),绑定到主梁单元组。
6. **创建活载工况**(`live.case.create`),配置横向折减 + 子工况 + 车道数。
7. **把沉降组、车道、活载工况名写入建模状态**(`loads` 字段)。

> 本模块不创建主梁、单元、钢束,只配置它们要承受的额外条件。

## 沉降分析

### 沉降组

```python
sg = engine.settlement.group.create(
    "桥墩1沉降组",          # 组名
    1.500e-02,              # 沉降量(m),15mm
    64,                     # 节点编号(varargs,不是 list)
)
```

**`name`、`val` 后是 varargs 节点**,不是 list。

**命名约定**:按位置命名,让 `_10` 阶段按名 include。如 `桥墩1沉降组`、`桥台1沉降组`。

**典型沉降值**:

| 部位 | 沉降量 | 说明 |
|---|---|---|
| 中墩 | 10~15mm | 桥墩沉降,典型 15mm |
| 桥台 | 5~10mm | 桥台沉降,通常小于中墩 |
| 相邻墩差异沉降 | 5~10mm | 决定是否需要设置差异沉降组 |

### 沉降工况

```python
st = engine.settlement.create("沉降")
st.include("a", "桥墩1沉降组", "桥墩2沉降组", "桥台1沉降组", "桥台2沉降组")
#                       ^^^^^^^^ op 必填
```

`Settlement.include(op, *group_names)` 的 `op` 是**第一个位置参数**:`"a"`=添加、`"r"`=移除。**不传 op 会报 TypeError**。

也可以用 `st.remove("name1", "name2")` 等价于 `st.include("r", ...)`。

## 移动荷载体系

```python
engine.live.grade.create_highway(
    name="移动荷载体系",                       # 体系名称(任意,建议带桥型/项目标识)
    code="JTGD60_2015",                       # 规范(默认 JTGD60_2015)
    live_load_type="HIGHWAY_I",               # 公路-I 级(也可用 "HIGHWAY_II")
)
```

| `code` | 规范 |
|---|---|
| `JTGD60_2015` | 公路桥涵设计通用规范(中国 2015) |
| `JTGD60_2004` | 公路桥涵设计通用规范(2004 老版) |

通用入口 `live.grade.create(name, code, live_load_type, ...)` 按 `live_load_type`(`"HIGHWAY_I"`/`"HIGHWAY_II"`/`"VEHICLE"`/`"CROWD"`/`"FATIGUE_*"`/`"VG"`)路由到 `create_highway`/`create_vehicle`/`create_crowd`/`create_fatigue`/`create_custom`,关系同其他模块:只多一个路由参数,其余参数与对应 `create_*` 完全一致。日常推荐 `create_*`;`create()` 适合按配置表/循环动态派发。

| `live_load_type` | 含义 |
|---|---|
| `HIGHWAY_I` | 公路-I 级(重载) |
| `HIGHWAY_II` | 公路-II 级(轻载) |
| `VEHICLE` | 车辆荷载等级 |
| `FATIGUE_I` / `FATIGUE_II` / `FATIGUE_III` | 疲劳荷载等级 |

## 车道线

通用入口 `live.lane.create(name, type, ...)` 按 `type`(`"VE"`/`"TCB"`)路由到 `create_ve`/`create_tcb`,关系同其他模块:只多一个路由参数,其余参数与对应 `create_*` 完全一致。

```python
engine.live.lane.create_ve(
    name="车道1",                  # 车道名
    length=24.46,                  # 车道长度(m)
    wheel=1.80,                    # 车轮间距(m)
    orientation=1,                 # 方向:-1=向后 / 0=往返 / 1=向前
    ref=0,                         # 参考:0=参照单元组 / 1=参照样条曲线
    ref_elems="主梁单元",          # 主梁单元组名(必须等于 `_6` 的组名,ref=0 时必填)
    offset_y=0.00,                 # y 偏置(m)
    offset_z=0.00,                 # z 偏置
    spline_name=None,              # 样条曲线名(ref=1 时必填)
)
```

**关键约束**:

- `ref_elems` **必须等于** `osis-module-element` 的 `element.group.create('主梁单元', 'c')` 创建的组名
- `length` 通常等于单跨跨径(或最大跨径)
- `offset_y` 按车道横向位置给定(多车道项目按需配置)

### 多车道布局

**车道数、车道横向位置、是否需要中载+左右偏载工况由桥型层 + 桥宽决定**。本模块负责按方案创建车道,不在此层决定具体车道数。

## 活载工况

`live.case.create` 返回 `LiveCase` 对象;子工况配置、横向折减、车道数范围都在对象上调。

```python
lc = engine.live.case.create(
    name="车道荷载包络",           # 工况名
    code="JTGD60_2015",           # 规范(默认 JTGD60_2015)
    sub_cmb_type=1,               # 子组合类型:1=单独(包络,默认) / 0=组合(相加)
)

# 横向折减系数(2~10 车道对应系数)
lc.set_trans_reduction_factors(1.20, 1.00, 0.78, 0.67, 0.60, 0.55, 0.52, 0.50, 0.50, 0.50)
# 上面是 varargs,不是 list

# 子工况(对每个偏载工况生成一个)
lc.create_sub(
    sub_name="车道荷载工况1",      # 子工况名
    grade_name="移动荷载体系",     # 移动荷载体系名(由桥型层给)
    scalar=0.65,                   # 横向分布系数(命令流 LiveAnalInc 的 scalar;非笼统缩放)
    calc_mu=True,                  # 是否计算冲击系数
    bridge_type="CUSTOM",          # 桥型(用于计算冲击系数)
    mu_params=[1.440000],         # 冲击系数参数(根据 bridge_type 不同)
    lane_names=["车道1", "车道2"],  # 引用车道名(varargs 也可)
)

# 加载车道数范围
lc.set_lane_count("车道荷载工况1", 0, 2)  # 0~2 车道
```

### 横向折减系数

`set_trans_reduction_factors(*factors)` 索引 = 加载车道数 - 1:

| 加载车道数 | 折减系数 |
|---|---|
| 1 | 1.20 |
| 2 | 1.00 |
| 3 | 0.78 |
| 4 | 0.67 |
| 5 | 0.60 |
| 6 | 0.55 |
| 7 | 0.52 |
| 8 | 0.50 |
| 9 | 0.50 |
| 10 | 0.50 |

> 数组长度要 ≥ 实际车道数,否则报索引越界。

### 横向分布系数(`scalar`)

`create_sub(..., scalar=…)` 与 `include("a", sub, grade, scalar, …)` 里的 **`scalar` 即横向分布系数**(对应命令流 `LiveAnalInc`),由桥型层按梁位给定。预制小箱梁典型:中梁 `0.65`、边梁 `0.85`。不要当成无意义的笼统缩放系数、也不要默认 `1.0`。

### 冲击系数 μ

| `bridge_type` | 含义 | `mu_params` |
|---|---|---|
| `"CUSTOM"` | 自定义(直接给 μ 值) | `[mu_value]` |
| `"SIMPLE"` | 简支梁桥 | `[桥长, 弹模, 惯性矩, 质量]` |
| `"CONTINUOUS"` | 连续梁桥 | `[常数a, 常数b, 桥长, 弹模, 惯性矩, 质量]` |
| `"ARCH"` | 拱桥 | `[拱厚变化系数, 矢跨比, 桥长, 弹模, 惯性矩, 质量]` |
| `"CABLE_STAYED"` | 斜拉桥(无辅助墩) | `[计算常数, 主跨跨径]` |
| `"CABLE_STAYED_AUS"` | 斜拉桥(有辅助墩) | `[计算常数, 主跨跨径]` |
| `"SUSPENSION"` | 悬索桥 | `[主跨跨径, 弹模, 惯性矩, 主缆水平拉力, 质量]` |

`calc_mu=True` 让 OSIS 按规范自动计算;`calc_mu=False` 时直接用 `mu_params` 第一个值。

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `loads` 字段(沉降组/工况名、移动荷载体系、车道清单、活载工况与子工况映射)。

## 失败模式

- **`ref_elems` 组不存在** —— 车道引用组名与 `osis-module-element` 不一致
- **`车道荷载包络`未在阶段激活** —— `_10` 中漏 `define_analysis(1, 'LIVE', '车道荷载包络')`
- **`Settlement.include` 漏 op** —— 必须传 `"a"` 或 `"r"`

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 桥型层 → 本模块 | 沉降值、车道数、活载等级、横向折减、**横向分布系数** |
| 上游 `osis-module-element` | `主梁单元` 组名(车道 `ref_elems` 引用) |
| 上游 `osis-module-node` | 桥墩/桥台节点编号(沉降组绑定) |
| 下游 `osis-module-stage` | 沉降工况名、活载工况名(阶段 `define_analysis` 引用) |

> **横向分布系数传递**:桥型层定值(如中梁 0.65、边梁 0.85),经 `create_sub(scalar=值)` 或 `include(..., scalar, ...)` 写入。
