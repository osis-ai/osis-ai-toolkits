---
name: osis-module-material
description: 材料定义模块。生成 `prep/_3_material.py`,定义混凝土/钢材/钢筋/预应力钢绞线及收缩徐变特性。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-material

> 材料模块。等级与规范由桥型层 + 项目规范决定;签名、可选 `code`/`grade` 用 `api_read` 查。

## 接到任务后,按顺序做

1. **从 `profile` 读取**:混凝土等级(主梁/桥墩)、钢筋等级、预应力钢绞线等级、规范。
2. **创建收缩徐变**(`engine.prop.creep_shrink.create`),每个混凝土等级一条。
3. **创建材料**:混凝土 `create_conc`、钢材 `create_steel`、钢筋 `create_rebar`、钢绞线 `create_prestressed`;规格化接口表达不了时才用 `create_custom`。
4. **把材料编号、规格、规范写入建模状态**。

> 不在本模块决定材料用于哪些单元 —— 那是 `_6_element` 的事,按 `mat` 引用。

## 写法

`create_*` 第一个位置参数是 `no`(材料编号),不是 `name`;传 `None` 自动分配(当前最大编号 +1)。

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

## 收缩徐变要点

- 参数一律用关键字写,不要按位置传(参数顺序随 pyosis 版本变过)。
- `fcuk` 在收缩徐变里,不在材料里:**不同强度等级的混凝土各建一条收缩徐变**,别让 C55 和 C40 共用一个编号。
- **没有加载龄期参数**。加载龄期由施工阶段激活单元时的龄期给出。
- `shrink_birth` 是 `birth_by_shrinking` 的旧写法,新代码写 `birth_by_shrinking`。
- 默认值:`avg_humidity` 70~75、`birth_by_shrinking=3`;项目另有规定时按项目。

阻尼比默认:混凝土/钢绞线 `0.05`、精轧螺纹钢 `0.02`。

## 失败模式

- **`crep_shrk` 引用不存在的收缩徐变** —— 先 `creep_shrink.create`,再 `create_conc(crep_shrk=...)`
- **规范代码拼写错** —— `JTG3362_2018`,不是 `JTG_3362_2018`
- **材料号冲突** —— 多个 `create_*` 传了相同 `no`,后建的覆盖前建

(其他见 `osis-engine/references/error_diagnosis.md`)
