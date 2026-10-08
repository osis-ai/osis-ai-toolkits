---
name: osis-module-stage
description: 施工阶段模块。生成 `prep/_10_stage.py`,创建施工阶段、定义每个阶段激活/钝化的单元组/边界组/荷载/钢束/分析工况,处理体系转换(临时锚固解除、永久约束激活、合龙)。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-stage

> 施工阶段模块。决定有多少个阶段、每个阶段激活/钝化哪些组,处理体系转换时序。

## 接到任务后,按顺序做

1. **从桥型层读取阶段序列**(CS1~CSn 名称、时长、每个阶段的主要动作)。
2. **创建施工阶段**(`stage.create`),**显式指定 `no=` 编号**(必须连续,无自动编号)。
3. **对每个阶段,在返回的 Stage 对象上调 `define_element/define_boundary/define_loadcase/define_analysis`**,定义该阶段激活/钝化哪些组。
4. **把阶段编号、时长、激活清单写入建模状态**(`stages` 字段)。

## 公共约定

**阶段编号必须显式传**,**编号必须连续**(CS1=1, CS2=2, ...)。OSIS 不做自动编号。

```python
stg = engine.stage.create(
    no=1,                    # 阶段编号(必填、必连续)
    name="CS1_下部及0号段",  # 阶段名
    duration=30,             # 持续时间(天)
)
```

`create` 返回 `Stage` 对象;**所有 `define_*` 都是在 Stage 对象上调,不是 manager**。

## Stage 对象方法

### define_element(单元组激活/钝化)

```python
stg.define_element(
    op,                      # 1=添加 / 0=移除
    type,                    # 1=激活 / 0=钝化
    group_name,              # element 组名(必须等于 `_6` 的组名)
    birth=None,              # 龄期(op=0 时需要 None)
    part=None,               # 组合结构分部:0=全部 / 1=钢材 / 2=混凝土
)
```

**字面量**:`op ∈ {0, 1}`;`type ∈ {0, 1}`(1=activate, 0=deactivate)。

### define_boundary(边界组激活/钝化)

```python
stg.define_boundary(
    op,                      # 1=添加 / 0=移除
    type,                    # 1=激活 / 0=钝化
    group_name,              # boundary 组名
)
```

### define_loadcase(荷载工况激活/钝化)

```python
stg.define_loadcase(
    op,                      # 1=添加 / 0=移除
    type,                    # 1=激活 / 0=钝化
    ref_lc_name,             # 参考当前施工阶段内的工况名
    lc_name,                 # 待操作的荷载工况名
)
```

### define_analysis(分析工况激活)

```python
stg.define_analysis(
    op,                      # 1=添加 / 0=移除
    type,                    # "MODAL"/"SETL"/"RSPEC"/"LIVE"/"BUCKLE"
    lc_name="",              # 荷载工况名(部分分析类型需要)
)
```

`type` 可选值:
- `MODAL` 模态
- `SETL` 沉降
- `RSPEC` 反应谱
- `LIVE` 活载
- `BUCKLE` 屈曲

## 阶段插入与删除

```python
engine.stage.insert(ref_no, position, name, duration)
# ref_no: 参考位置编号
# position: 0=前插, 1=后插(必填,不能省)

engine.stage.remove(no)             # 移除插入的阶段(不是原 create 的)
engine.stage.delete(no)             # 删除阶段(参数是阶段编号 int,不是名字)
```

> `StageManager` **没有 `rename` 方法**;改阶段名请用同 `no` 重新 `create(no, 新名, duration)`(同号覆盖,实测不报错)。

## 查询与局部修改

`engine.stage.get(no)` 返回 `Stage` 对象;工期字段是属性 **`.duration`**(无 `get_duration()`)。

**只改某阶段工期**:改 `prep/_10_stage.py` 里对应 `duration`,再按 `osis-engine` 跑 `prep/main.py`。

## 写 `_10` 前的引用核对(必做)

`_10` 是**纯引用模块**:它不创建任何对象,只按名字引用 `_6`/`_7`/`_8`/`_9` 已创建的组、工况、分析。名字差一个字(含中文、下划线、大小写)就会在阶段激活时报"xxx 不存在"。落笔前逐项核对,**全部命中才允许写**:

| `define_*` 参数 | 必须逐字等于 | 核对出处 |
|---|---|---|
| `define_element` 的 `group_name` | `_6` 中 `element.group.create(...)` 的组名 | 建模状态 `elements` + `_6_element.py` 文件 |
| `define_boundary` 的 `group_name` | `_7` 中边界组名 | 建模状态 `boundaries` + `_7_boundary.py` 文件 |
| `define_loadcase` 的 `lc_name` | `_8` 中 `engine.load.create(<名>, ...)` 的工况名 | 建模状态 `loads` + `_8_loadcase.py` 文件 |
| `define_analysis` 的 `lc_name` | `_9` 中分析工况名 | 建模状态 `loads` + `_9_analysis.py` 文件 |

特别注意:

- **工况名 ≠ 钢束名**。"预应力腹板束"是 `_8` 的**荷载工况名**;"N1-1"/"T2-1" 是**钢束 shape 名**。`define_loadcase` 只引用工况名,**绝不引用钢束 shape 名**。
- 桥型层给定的工况名(如 T 梁的 `预应力腹板束`/`预应力顶板束`)是 `_8` 与 `_10` 之间的**契约名**:两处都必须逐字出现,不得同义改写(不写成"腹板束"、"PST"、"预应力_腹板束")。
- **不要凭记忆写名字**:打开 `_8_loadcase.py` 等实际文件,逐条 `load.create` 对照后再写。

## 报告状态

→ `osis-engine` §维护建模状态 表,本 module 写 `stages` 字段(阶段编号、名称+时长、单元/边界/荷载/分析激活映射、体系转换时序)。

## 失败模式

- **阶段编号不连续** —— OSIS 要求 1~N 连续;中间缺号会报"阶段不存在"
- **`group_name` 不存在** —— 引用的单元/边界/荷载组名不在 `_6`/`_7`/`_8` 中
- **`该工况中不存在名为 xxx 的预应力板束/荷载`(命令流出现 `StgLC,...` 报错)** —— `define_loadcase` 引用了 `_8` 未创建或拼写不一致的工况名,或误把钢束 shape 名当工况名。**修复动作**:打开 `_8_loadcase.py` 逐条 `load.create` 对照,把 `_10` 的引用名改到逐字一致(或反向改 `_8`),然后跑 `main.py` 写回。禁止不改代码直接重跑 `main.py`(见 `osis-engine` §失败修复流程)
- **体系转换时序错** —— 永久约束在临时锚固之前激活,导致结构超静定异常
- **钢束张拉阶段早于构件激活** —— 钢束 `layout` 报错"钢束进入未激活单元"
- **`同一阶段内不允许重复激活单元组[xxx]`** —— 该阶段里这个组已经激活过,又对同一阶段 `define_element`。常见于单跑 `_10`(没经过 `main.py` 的 clear)或 `_10` 里同阶段重复 `define_element`。删掉重复行后跑 `main.py`;不要对着已有阶段再跑一遍 `define_*`

(其他见 `osis-engine/references/error_diagnosis.md`)

## 协作

| 上下游 | 交接 |
|---|---|
| 桥型层 → 本模块 | 阶段序列(CS1~CSn 名称、时长、主要动作) |
| 上游 `osis-module-element` | 单元组名(逐阶段激活) |
| 上游 `osis-module-boundary` | 边界组名(临时/永久约束) |
| 上游 `osis-module-loadcase` | 工况名(自重、二期、预应力等) |
| 上游 `osis-module-analysis` | 分析工况名(沉降、活载) |
