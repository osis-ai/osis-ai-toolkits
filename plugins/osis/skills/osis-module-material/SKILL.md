---
name: osis-module-material
description: 材料定义模块。生成 `prep/_3_material.py`,定义混凝土/钢材/钢筋/预应力钢绞线的规格,以及收缩徐变特性。处理 4 类材料创建 API(create_conc/create_steel/create_rebar/create_prestressed)的常用规格选择。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-material

> 材料模块。提供 4 类材料规格模板,具体选哪个由桥型层 + 项目规范决定。

## 接到任务后,按顺序做

1. **从 `profile` 读取**:混凝土等级(主梁/桥墩)、钢筋等级、预应力钢绞线等级、规范。
2. **创建收缩徐变**(`prop.creep_shrink.create`),用于施工阶段时间效应计算。
3. **创建混凝土材料**(`create_conc`),主梁和桥墩通常用不同等级。
4. **创建钢材/钢筋**(`create_steel` / `create_rebar`)。
5. **创建预应力钢绞线**(`create_prestressed`)。
6. **把材料编号、规格、规范写入建模状态**(`profile` + `sections` 字段)。

> 不在本模块决定材料应用于哪些单元 —— 那是 `_6_element` 的事,按 `nMat` 引用。

## 公共约定

所有 `create_*` 方法的**第一个位置参数都是 `no`(材料编号)**,不是 `name`。`no` 可显式传,也可传 `None` 让 OSIS 自动分配(自动取当前最大编号+1)。

```python
# 显式指定编号
mat = engine.material.create_conc(1, "C50混凝土", "JTG3362_2018", "C50")

# 自动分配编号
mat = engine.material.create_conc(None, "C50混凝土", "JTG3362_2018", "C50")
mat.no   # 自动分配的编号
```

## 收缩徐变

每个混凝土材料都引用一个 `creep_shrink` 编号。`creep_shrink` 通过 `engine.prop` 访问:

```python
engine.prop.creep_shrink.create(
    no=1,
    name="收缩徐变",
    avg_humidity=75.0,      # 平均环境湿度(%)
    birth_time=7,           # 加载龄期(天)
    type_coeff=5.0,         # 类型系数
    shrink_birth=3,         # 收缩起始龄期(天)
)
```

**典型参数**:

| 项目 | avg_humidity | birth_time | shrink_birth |
|---|---|---|---|
| 主梁 | 70~75% | 7d | 3d |
| 桥墩 | 70~75% | 7d | 3d |

> 具体项目参数由桥型层 / 项目规范给定。

## 4 类材料规格模板

### 混凝土 `create_conc`

```python
mat = engine.material.create_conc(
    no,                                    # 材料编号(显式或 None)
    name="C50",                            # 材料名
    code="JTG3362_2018",                   # 规范
    grade="C50",                           # 等级
    crep_shrk=1,                           # 收缩徐变编号
    dmp=0.050,                             # 阻尼比
)
```

**`code` 可选值**:`JTG3362_2018` / `JTGD62_2004`

**`grade` 可选值**:`C15, C20, C25, C30, C35, C40, C45, C50, C55, C60, C65, C70, C75, C80`

**常见等级**(由桥型层 + 项目规范决定):

| 等级 | 应用 |
|---|---|
| C40 | 低等级桥墩 |
| C50 | 主梁、桥墩(常见) |
| C55 | 大跨主梁 |
| C60 | 特大桥 |

### 钢材 `create_steel`

```python
mat = engine.material.create_steel(
    no,
    name="Q345",
    code="JTGD64_2015",                   # 钢结构规范
    grade="Q345",
    dmp=0.050,
)
```

**`code` 可选值**:`JTGD64_2015`
**`grade` 可选值**:`Q235, Q345, Q390, Q420`

桥梁钢结构用 `Q345` / `Q420`(高强)。

### 钢筋 `create_rebar`

```python
mat = engine.material.create_rebar(
    no,
    name="HRB400",
    code="JTG3362_2018",
    grade="HRB400",
    dmp=0.050,
)
```

**`code` 可选值**:`JTG3362_2018` / `JTGD62_2004`
**`grade` 可选值**(依规范):
- `JTG3362_2018`:`HPB300, HRB400, HRBF400, RRB400, HRB500`
- `JTGD62_2004`:`R235, HRB335, HRB400, KL400`

### 预应力钢绞线 `create_prestressed`

```python
mat = engine.material.create_prestressed(
    no,
    name="Strand1860",
    code="JTG3362_2018",
    grade="Strand1860",
    dmp=0.050,
)
```

**`code` 可选值**:`JTG3362_2018` / `JTGD62_2004`
**`grade` 可选值**(依规范):
- `JTG3362_2018`:`Strand1720, Strand1860, Strand1960, Wire1470, Wire1570, Wire1770, Wire1860, Rebar785, Rebar930, Rebar1080`
- `JTGD62_2004`:`Strand1860, Wire1670, Wire1770, Rebar785, Rebar930`

阻尼比常用:混凝土/钢绞线 `0.050`、精轧螺纹钢 `0.020`。

### 自定义材料(少见)

仅当规格化模板无法表达时:

```python
engine.material.create_custom(
    no,                          # 编号
    name="刚性材料",
    e=2.06e14,                   # 弹性模量(Pa)
    g=0,                         # 剪切模量
    mu=0,                        # 泊松比
    exp_coeff=0,                 # 线膨胀系数(1/℃)
    unit_weight=0,               # 容重(N/m³)
    density=0,                   # 质量密度(kg/m³)
    dmp=0,                       # 阻尼比
)
```

## 通用入口 `engine.material.create`

```python
engine.material.create(no, name, type, *args, **kwargs)
```

按 `type` 派发到具体 `create_*`:

| `type` | 派发到 | 用途 |
|---|---|---|
| `"CONC"` | `create_conc` | 混凝土 |
| `"STEEL"` | `create_steel` | 钢材 |
| `"PRESTRESSED"` | `create_prestressed` | 预应力 |
| `"REBAR"` | `create_rebar` | 钢筋 |
| `"CUSTOM"` | `create_custom` | 自定义 |

**`create_*` 与 `create()` 的关系**:两者只差一个 `type` 路由参数,其余参数(顺序、含义、默认值)完全一致——`create_*` 等价于 `create()` 帮你填好了 `type`。例:`create(1, "C50", "CONC", "JTG3362_2018", "C50")` ≡ `create_conc(1, "C50", "JTG3362_2018", "C50")`。日常推荐 `create_*`(IDE 补全友好、签名明确);`create()` 适合按配置表或循环动态派发不同类型对象。

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `profile` + `sections` 字段(材料编号、规格、规范、收缩徐变引用)。

## 失败模式

- **`nCrepShrk` 引用不存在的收缩徐变** —— 必须先 `creep_shrink.create`,再 `create_conc(crep_shrk=...)`
- **规范代码拼写错** —— `JTG3362_2018`(混凝土),不是 `JTG_3362_2018`
- **材料号冲突** —— 多个 `create_*` 传了相同 `no`,后建的覆盖前建

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 桥型层 → 本模块 | 混凝土等级、钢筋等级、钢绞线等级、规范 |
| 上游 `osis-module-control` | 收缩徐变开关(`calc_shrink` / `calc_creep`) |
| 下游 `osis-module-element` | 材料号(`nMat`) |
| 下游 `osis-module-tendon` | 钢绞线材料号(`mat`) |
