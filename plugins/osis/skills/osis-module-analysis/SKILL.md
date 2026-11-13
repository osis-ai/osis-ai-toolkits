---
name: osis-module-analysis
description: 分析设置模块。生成 `prep/_9_analysis.py`,创建沉降组(支座不均匀沉降)和活载分析(车道 + 移动荷载体系 + 活载工况 + 横向折减 + 冲击系数)。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-analysis

> `prep/_9_analysis.py`:`build_analysis(engine)`。沉降值、车道布置、横向分布系数、基频由桥型层和项目给;这里创建的沉降工况名、活载工况名被 `_10` 的 `define_analysis` 按名引用。

## 沉降

```python
engine.settlement.group.create("桥墩1沉降组", 0.015, 64, 65)   # name, 沉降量(m), 节点 varargs(不是 list)
st = engine.settlement.create("沉降")
st.include("a", "桥墩1沉降组", "桥台1沉降组")                    # op 是第一个位置参数,必填:"a" 添加 / "r" 移除
```

## 移动荷载体系与车道

```python
engine.live.grade.create_highway(name="移动荷载体系", code="JTGD60_2015", live_load_type="HIGHWAY_I")
# create_ve / create_tcb 的形参与命令流 InflAlgo 字段逐位对应,全用位置参数。
# ref=0 尾部三个:参照单元组名, offset_y, offset_z;ref=1 尾部两个:组名, 样条曲线名。
engine.live.lane.create_ve(
    "车道1", 24.46, 1.80, 1, 0,
    "主梁单元", 0.0, 0.0,   # 参照单元组必须是 `_6` 建的组名
)
```

- 便捷入口 `live.lane.create("车道1", "VE", 24.46, 1.80, 1, 0, "主梁单元", 0.0, 0.0)` 等价。
- 第 2 个参数 `length` 在 docstring 里是"桥梁跨度"(m)。

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

- **横向折减系数**:第 k 个值对应加载 k 条车道,最多 10 个,个数不少于实际车道数。上面这组是 JTG D60-2015 的值,各桥型通用。
- **横向分布系数** = `create_sub` / `include` 的 `scalar`(命令流 `LiveAnalInc`)。docstring 叫它"缩放系数"、默认 1.0;**单梁模型不要沿用 1.0**,按桥型层给的梁位系数填。
- **冲击系数**:`bridge_type` 决定 `mu_params` 的含义。`CUSTOM` 直接给基频,由基频算 μ;其余类型的参数顺序用 `api_read live.case.create_sub` 查。

## 失败模式

- **车道参照组不存在** —— 组名与 `_6` 不一致
- **活载没有结果** —— `_10` 运营阶段漏了 `define_analysis(1, "LIVE", "车道荷载包络")`
- **`Settlement.include` 抛 `TypeError`** —— 漏了 op
