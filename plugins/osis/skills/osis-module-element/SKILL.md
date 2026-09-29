---
name: osis-module-element
description: 单元建模模块。生成 `prep/_6_element.py`,创建梁单元、分配材料/截面、组建分组。处理"组名 = 跨模块契约"的核心规则——`_6` 创建的组名被 `_8`(钢束投影)、`_9`(车道引用)、`_10`(阶段激活)三处引用,任一处差一个字就报"组不存在"。**具体建哪些组、组名清单由桥型层 SKILL 决定**,本模块负责按清单建组并保证跨模块命名一致。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-element

> 单元模块。负责把节点连成梁单元,按用途建分组。分组命名是跨模块协作的关键契约。

## 接到任务后,按顺序做

1. **从建模状态读取**:节点编号、截面编号、材料编号。
2. **创建梁单元**(`create_beam3d`),逐对节点连线,显式指定 `no=`、`nMat=`、`nSec1=`/`nSec2=`。
3. **组建分组**(`element.group.create`)。**所有分组名要预登记**,让下游模块按名引用。
4. **分配构件理论厚度**(`prop.assign_component_thickness`),按单元两端截面算完再分批赋(公式与重算规则见 §分配构件理论厚度)。
5. **把单元编号、分组名写入建模状态**(`elements` 字段)。

> 单元是协作链中间环节,**必须**为下游需求提前建好分组,不能"用到再建"。

## 单元创建

```python
e = engine.element.create_beam3d(
    no,                  # 单元编号(显式,第一个位置参数)
    node1, node2,        # I 端、J 端节点编号
    nMat,                # 材料号
    nSec1, nSec2,        # I 端、J 端截面号(等截面单元两端相同,变截面单元两端不同)
    nYTrans=1, nZTrans=1, # 截面过渡方式(1=线性插值)
    dStrain=0.0, bFlag=0, dTheta=0, bWarping=0,
)
```

- `node1`/`node2` 必须是 `_5_node` 已建的节点
- `nMat` 必须是 `_3_material` 已建的材料
- `nSec1`/`nSec2` 必须是 `_4_section` 已建的截面
- 单元编号 `no` 显式,从 1 开始,逐个加 1
- 也可用通用入口 `engine.element.create(no, "BEAM3D", node1, node2, nMat=..., nSec1=..., nSec2=...)`(`type` 字符串派发)

## 通用入口 `engine.element.create`

```python
engine.element.create(no, type, *args, **kwargs)
```

按 `type` 派发到具体 `create_*`:

| `type` | 派发到 | 用途 |
|---|---|---|
| `"BEAM3D"` | `create_beam3d` | 梁柱单元 |
| `"TRUSS"` | `create_truss` | 桁架单元 |
| `"SPRING"` | `create_spring` | 弹簧单元 |
| `"CABLE"` | `create_cable` | 拉索单元 |
| `"SHELL"` | `create_shell` | 壳单元 |

**`create_*` 与 `create()` 的关系**:两者只差一个 `type` 路由参数,其余参数(顺序、含义、默认值)完全一致——`create_*` 等价于 `create()` 帮你填好了 `type`。例:`create(1, "BEAM3D", node1, node2, nMat, nSec1, nSec2)` ≡ `create_beam3d(1, node1, node2, nMat, nSec1, nSec2)`。日常推荐 `create_*`(IDE 补全友好);`create()` 适合按配置表/循环动态派发。

## 弹簧单元(墩梁连接等)

`create_spring` 用于桥墩/桥台节点与主梁节点的弹性连接。**参数不是 KX~KRZ 6 个刚度**,而是每个方向带一个**启用标志** + **刚度值**:

```python
e = engine.element.create_spring(
    no,                 # 单元编号
    node1, node2,       # 节点编号
    bLinear=1,          # 是否线性(0/1)
    dx=1e13,            # UX 方向刚度(m 刚度极大值 = 固定)
    dy=1e13,
    dz=1e13,
    rx=1e16,            # RX 方向扭转刚度
    ry=1e16,
    rz=1e16,
    beta=0.0,           # 阻尼
)
```

- **刚度极大值 = 固定**:平动方向 `1e13`,转动方向 `1e16`
- **典型用法**:墩梁固结时,`dx=dy=dz=1e13`,`rx=ry=rz=1e16`,`bLinear=1`

## 组名 = 跨模块契约(核心规则)

**`_6` 创建的组名,被以下模块引用**:

| 引用方 | 用途 | 引用方式 |
|---|---|---|
| `_8_loadcase` (钢束) | 钢束投影 `tendon.shape.create_arc3d(element_group='xxx')` | 组名 |
| `_9_analysis` (车道) | 车道引用 `live.lane.create_ve(ref_elems='xxx')` | 组名 |
| `_10_stage` (阶段) | 阶段激活 `stage.define_element(group_name='xxx')` | 组名 |

**组名逐字一致**。任一处差一个字符(中文/下划线/数字/大小写),报"组不存在"或"load group not found"。

写下游模块时直接照状态里记录的组名用,**不要另起新名、不要改大小写、不要改下划线、不要删前缀**。

## 三类用途的分组(命名由桥型层决定)

按下游引用方拆三类。**具体组名清单由桥型层 SKILL 决定**。本模块负责**按桥型层给的组名建组**。

| 用途 | 引用方 | 命名风格(参考) |
|---|---|---|
| 施工构件 | `_10_stage` | 描述用途/位置的中文名 |
| 钢束投影 | `_8_loadcase` | 钢束名 + `CurveGp` / `Gp` |
| 车道引用 | `_9_analysis` | 描述位置的中文名(常 `主梁单元`) |

**组名逐字一致**。建好后立即写入状态,下游照状态引用。

## 钢束投影组细化

钢束的 element_group 必须**精确覆盖钢束控制点 x 范围内的所有单元**。如果钢束 x 跨多个节段,该组要包含这些节段的所有单元。

常见错误:组范围不足,导致 `tendon.shape.layout('GLOBAL')` 报"控制点坐标超出参照单元组的坐标范围"。

## 单元分组的三步法

`element.group.create` **必须传 `op` 参数**(底层 OSIS 要求),常见值 `"c"`(创建)、`"a"`(添加)、`"s"`(替换)、`"r"`(移除)、`"aa"`(全加)、`"ra"`(全删)、`"m"`(改名)、`"d"`(删除)。

```python
# 1. 创建组(组名由桥型层给定,op 必填)
eg = engine.element.group.create("主梁单元", "c")

# 2. 在返回的 ElementGroup 对象上添加成员(varargs,不是 list)
eg.add(1, 2, 3, 4, 5)              # 离散编号
eg.add("1to58")                    # 字符串区间
eg.add("1to46", "60to80")          # 多段

# 3. 验证
print(engine.element.group.all())
```

> **`create(name, "c")` 不是幂等的**:同名组已存在时再 `"c"` 报"单元组已经存在"(实测)。需要单模块重跑 `_6` 时,先 delete-if-exists:
> ```python
> if engine.element.group.get("主梁单元"):
>     engine.element.group.delete("主梁单元")   # 组删除无依赖检查,可直接用
> eg = engine.element.group.create("主梁单元", "c")
> ```
> 详见 `osis-engine/references/incremental_rerun.md`。

**`eg.add` 接受 varargs**,不传 list。字符串区间如 `'1to46'`、`'3to18'` 直接传字符串。

> **两种写法等价(实测)**:对象风格 `eg = create(name, "c"); eg.add("11to18", "31to38")` 与 manager 两步风格 `create(name, "c"); create(name, "a", "11to18", "31to38")`(模板 `.out` 直译写法)底层是同一条 `EleGrp,name,a,...` 命令,效果完全相同,按习惯任选。
>
> 两个常见误用(都会报错):
> - **`engine.element.group.add(...)` —— manager 上没有 `add`**(只有 `create/delete/get/all/count`),`add/remove/replace/rename` 都在 `create()`/`get()` 返回的 `ElementGroup` 对象上调,在 manager 上调会抛 `AttributeError`
> - **以为 `add` 只接受 int**——`def add(self, *elements: int)` 的类型标注写窄了,函数体把参数原样透传给命令,字符串区间(`"1to49"`)实测可用

## 分配构件理论厚度

```python
engine.prop.assign_component_thickness(
    thickness,            # 理论厚度 h(m)
    op,                   # 'a'=添加/覆盖(推荐), 's'=替换(docstring有;部分OSIS会报编辑有误), 'r'=移除
    1, 2, 3, 4, 5,        # 单元编号 varargs(支持 "1to5" 区间字符串,不是 list)
)
```

**理论厚度用于收缩徐变计算**(pyosis docstring 原话),混凝土梁单元必须分配,不是可省的装饰。

**L0 改厚度实测**:模板与现网一律用 `"a"`。docstring 写 `"s"`=替换,但对已分配单元执行 `"s"` 可能报「编辑构件厚度有误」;改用 `"a"` 可覆盖该单元厚度(同值单元可能被 OSIS 合并到同一 `AsgnCompThk` 行)。

### 模板已证实口径(箱梁 / CONVENTIONALBOX)

1. **截面理论厚度**
   \[
   h_{\mathrm{sec}} = \frac{2A}{u_{\mathrm{outer}} + u_{\mathrm{in}}/2}
   \]
   - \(A\) = 净混凝土面积(外轮廓面积 − 各内腔面积之和)
   - \(u_{\mathrm{outer}}\) = 外轮廓周长
   - \(u_{\mathrm{in}}\) = **全部**内腔周长之和(单箱单室通常 1 个内环;接口若拆成左右两段内环,周长要相加)
   - **不要**用 \(u_{\mathrm{outer}}+u_{\mathrm{in}}\)(全加内周长)——与本系列模板数值对不上

2. **单元理论厚度**(写入 `assign_component_thickness` 的值)
   \[
   h_{\mathrm{elem}} = \frac{h(nSec1) + h(nSec2)}{2}
   \]
   即取该梁单元 **I/J 两端截面** \(h_{\mathrm{sec}}\) 的算术平均。等截面单元两端相同 → \(h_{\mathrm{elem}}=h_{\mathrm{sec}}\)。变截面/Taper 单元两端不同 → 必须平均,禁止只拿一端或按"同截面号分批共用一个值"。

3. **分批赋给单元**:把 \(h_{\mathrm{elem}}\) 相同的单元号收成一组,一次 `assign_component_thickness` 调用(模板 `_6_element.py` 的厚度块就是这种分组)。相邻节段值不同是正常的。

### 怎么取 A、u(pyosis 无专用 get_area)

`section.get(no).prop` 经常是 `None`,**不要空等面积/周长字段**。可靠路径:

```python
import math
sec = engine.section.get(no)          # 或跑完 _4 后 GetSectionInfoByNos
rings = sec.contour                   # list[list[{x,y}, ...]]; [0]=外轮廓,其后=内腔

def _area_peri(pts):
    xs = [p["x"] for p in pts] + [pts[0]["x"]]
    ys = [p["y"] for p in pts] + [pts[0]["y"]]
    a = u = 0.0
    for i in range(len(pts)):
        a += xs[i] * ys[i + 1] - xs[i + 1] * ys[i]
        u += math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i])
    return abs(a) / 2.0, u

A_out, u_outer = _area_peri(rings[0])
A_in = u_in = 0.0
for ring in rings[1:]:
    a, u = _area_peri(ring)
    A_in += a
    u_in += u
A = A_out - A_in
h_sec = 2 * A / (u_outer + u_in / 2)
```

校验:改截面**之前**,用同一公式算模板已有截面,应能命中模板 `_6` 里对应单元的厚度(允许末位四舍五入差)。对不上先查轮廓环数/平均规则,不要改公式。

### 重算铁律

- **禁止照抄模板数值**:模板 `_6` 里的具体值是按**模板自己的截面**算好的。改了梁高、板厚或桥宽 → A、u 全变,必须按上式重算再写回 `_6`。
- 时机:`_4_section` 定稿并在 OSIS 中创建/更新截面之后,再读 `contour` 算厚度;最后写 `assign_component_thickness`。
- **写回**:改完 `_6` 后按 `osis-engine` 跑 `prep/main.py`。理论厚度参数用 `"a"`(与模板一致;勿盲信 `"s"`)。

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `elements` 字段(单元编号范围、分组清单、桥墩弹簧节点对、构件厚度)。

## 失败模式

- **`组不存在` / `load group not found`** —— 下游引用的组名在本 module 没建,或大小写/下划线/前缀不一致。对照状态里的组名清单
- **`形状控制点坐标超出参照单元组的坐标范围`** —— 钢束投影组范围不足,扩组范围
- **弹簧报"弹性连接报错"** —— 刚度值过小(应该 1e13/1e16)或 `bLinear=0`

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 上游 `osis-module-material` / `osis-module-section` / `osis-module-node` | 材料/截面/节点编号 |
| 下游 `osis-module-loadcase` | 钢束投影组、车道引用组 |
| 下游 `osis-module-analysis` | 车道引用组(主梁单元) |
| 下游 `osis-module-stage` | 全部施工构件组 |

**组名 = 跨模块契约**(见 osis-engine §会话硬约束):`_8` 钢束 `element_group`、`_9` 车道 `ref_elems`、`_10` 阶段 `define_element` 的 `group_name`,任一处差一个字报"组不存在"。建好后立即写入状态,下游照状态引用。
