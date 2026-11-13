---
name: osis-module-loadcase
description: 荷载工况模块。生成 `prep/_8_loadcase.py`,创建工况(自重/二期/温度/线荷载/节点力)并施加荷载,把钢束绑定到预应力工况。当总控按依赖顺序加载到本模块时使用。钢束的规格、曲线、形状见 `osis-module-tendon`。
---

# osis-module-loadcase

> `prep/_8_loadcase.py`:`build_loadcases(engine)`。有哪些工况、荷载值由桥型层和项目给。

## 工况

```python
lc = engine.load.create("主梁自重", "CS", 1.0)          # name, load_case_type, scalar
lc.create_gravity(x_coeff=0, y_coeff=0, z_coeff=-1.04)
```

- 荷载在 `load.create` 返回的 `LoadCase` 对象上加,不在 manager 上。
- 工况类型用 `api_read` 看 `load_case_type`。**自重、二期、预应力都用 `CS`**;均匀温度 `T`、梯度温度 `TG`;`SH`=收缩、`CR`=徐变;沉降类是 `STL`,不是 `EV`。
- **工况名是 `_8` 与 `_10` 的契约**:`_10` 的 `define_loadcase` 按名引用,逐字一致。桥型层或模板给定的工况名原样用,不同义改写。

## 荷载要点

参数名一律 snake_case。**很多参数的默认值不是 0,用到的方向全部显式传。**

- **自重** `create_gravity`:`x_coeff` / `y_coeff` 默认 1.0,必须显式传 0。系数乘 g,负=向下;`z_coeff=-1.04` 的 1.04 计入钢筋等超重。
- **线荷载** `create_line_load`:`coord_system` 默认 1(整体)、`load_type` 默认 1(离散)、`fx_i` / `fy_i` 默认 100,都要显式传。满布写 `load_type=0, offset_x_i=0, offset_x_j=1`。`entity` 只接受单个单元号,多单元用循环。
- **节点力** `create_nforce(entity, fx, fy, fz, mx, my, mz)`:`fx` 默认 100,显式传 0。同节点再建是更新,不新增。等价写法 `lc.create("NFORCE", node, fx, fy, fz, mx, my, mz)`。

## 温度

`entity` 只能传 **int 单号**,不支持 `"1to36"`,逐单元循环:

```python
lc = engine.load.create("整体升温", "T")
for i in elems:
    lc.create_uniform_temperature(i, direct="X", temp=20)   # X=整体升降温

lc = engine.load.create("正温度梯度", "TG")
for i in elems:
    lc.create_gradient_temperature(
        i, "Z", "R", 2,                                # entity, direct, g_temp_type, num —— 全部位置传
        1.7, 0.0, 14, 0.1, 5.5, 1.7, 0.1, 5.5, 0.4, 0,  # *param
    )
```

- `*param` 是 varargs,前 4 个参数全位置传。
- `g_temp_type` 是梁的参考位置(`"R"`/`"T"`/`"C"`/`"B"`),不是升温/降温。
- `num` = 折线段数;`*param` 每段一组 `(B, H1, T1, H2, T2)`(B 可空 `""`,H=距参考位置的距离,T=该处温度)。
- 项目没给时:整体升降温 ±20℃,梯度按规范。

## 预应力绑定

```python
lc = engine.load.create("预应力腹板束", "CS")
lc.create_prestress(
    entity="N1-1",               # 钢束 shape 名,不是工况名
    tension_type="BOTH",         # "BOTH"/"BEG"/"END"
    tension_force_type="ST",     # "ST"/"IF"
    beg=1.395e9, end=1.395e9,    # Pa。1395 MPa = 0.75 × 1860
)
```

- 等价写法 `lc.create("PST", <shape名>, <tension_type>, <tension_force_type>, <beg>, <end>)`。
- **shape 名和工况名是两个名字空间**:shape 名只出现在这里的 `entity`;工况名给 `_10` 用。`_10` 里永远不出现 shape 名。
- 项目没给时用上面的值:两端张拉、控制应力 1.395e9 Pa。

## 失败模式

- **按工况名查 `engine.result.*` 得到空表 / `未返回这些名字的结果`** —— 施工阶段结果不按原工况名存,而是 `_合计_<阶段名>`、`_恒载_<阶段名>` 等。先不传名字查一次,从 `loadCase` 列取实际名字
- **温度/线荷载施加失败** —— `entity` 传了字符串区间,改成循环
- **自重方向不对** —— `create_gravity` 没传 `x_coeff=0, y_coeff=0`
- **预应力不生效** —— 钢束 shape 没 `layout`,或张拉应力写成了 MPa
