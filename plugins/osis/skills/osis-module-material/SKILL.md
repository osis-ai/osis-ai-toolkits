---
name: osis-module-material
description: 材料定义模块。生成 `prep/_3_material.py`,定义混凝土/钢材/钢筋/预应力钢绞线及收缩徐变特性。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-material

> `prep/_3_material.py`:`build_materials(engine)`。等级由桥型层和项目给;可选的 `code` / `grade` 用 `api_read` 查。

```python
engine.prop.creep_shrink.create(
    1, "收缩徐变C50",
    fcuk=50e6,              # 28 天混凝土强度,按当前压力单位(默认 Pa)
    avg_humidity=75.0,      # 平均环境湿度(%),40~99
    type_coeff=5.0,         # 水泥种类系数
    birth_by_shrinking=3,   # 收缩开始龄期(天)
)
engine.material.create_conc(1, "C50", "JTG3362_2018", "C50", crep_shrk=1, dmp=0.05)
engine.material.create_rebar(2, "HRB400", "JTG3362_2018", "HRB400", dmp=0.05)
engine.material.create_prestressed(3, "Strand1860", "JTG3362_2018", "Strand1860", dmp=0.05)
```

- `create_*` 第一个位置参数是 `no`(材料编号),不是 `name`。同号再建是覆盖。
- 规格化接口(`create_conc` / `create_steel` / `create_rebar` / `create_prestressed`)表达不了时才用 `create_custom`。
- 规范代码写 `JTG3362_2018`、`GBT5224_2014`,没有多余下划线。
- 阻尼比:混凝土/钢绞线 `0.05`,精轧螺纹钢 `0.02`。

## 收缩徐变

- 先建收缩徐变,再建引用它的混凝土(`crep_shrk=编号`)。
- 参数用关键字写。
- `fcuk` 在收缩徐变里,不在材料里:**每个混凝土强度等级各建一条**,C55 和 C40 不共用。
- **没有加载龄期参数**:加载龄期由 `_10` 激活单元时的 `birth` 给。
- 项目没给时:`avg_humidity` 70~75、`type_coeff=5.0`、`birth_by_shrinking=3`。
