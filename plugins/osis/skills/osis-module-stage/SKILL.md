---
name: osis-module-stage
description: 施工阶段模块。生成 `prep/_10_stage.py`,创建施工阶段、定义每个阶段激活/钝化的单元组/边界组/荷载工况/分析工况,处理体系转换。当总控按依赖顺序加载到本模块时使用。
---

# osis-module-stage

> `prep/_10_stage.py`:`build_stages(engine)`。阶段序列、时长、每阶段动作由桥型层和项目画像给。`_10` 不创建对象,只按名字引用 `_6`/`_7`/`_8`/`_9` 建好的组、工况、分析。

## 写法

```python
stg = engine.stage.create(1, "CS1_主梁预制", 7)   # no 必填,从 1 连续,没有自动编号
stg.define_element(1, 1, "预制单元", 7.0, 0)     # op, type, 组名, 龄期 birth, part
stg.define_boundary(1, 1, "临时支座")            # op, type, 边界组名
stg.define_loadcase(1, 1, "", "预制单元自重")    # op, type, ref_lc_name, lc_name
stg.define_analysis(1, "LIVE", "车道荷载包络")   # op, 分析类型, 工况名
```

- `define_*` 在 `create` 返回的 Stage 对象上调,不在 manager 上。
- `op`:1=添加、0=移除;`type`:1=激活、0=钝化。
- `define_element` 的 `birth` 是激活时的龄期(天),移除时传 `None`。**弹簧单元组用 `0.0`**,否则报"弹性连接报错";混凝土单元组用激活时的实际龄期。
- `define_loadcase` 的第 3 个参数 `ref_lc_name` 一般传 `""`,第 4 个才是工况名。
- `define_analysis` 的类型:`MODAL` / `SETL` / `RSPEC` / `LIVE` / `BUCKLE`。
- 改阶段名:没有 `rename`,用同 `no` 重新 `create(no, 新名, duration)` 覆盖。
- 插阶段 `stage.insert(ref_no, position, name, duration)`,`position`(0=前插、1=后插)必填;`stage.delete(no)` 参数是编号。
- 阶段工期是属性 `.duration`,没有 `get_duration()`。
- **单跑 `_10`**:已有阶段上重跑 `define_*` 报「同一阶段内不允许重复激活单元组」。先 `engine.stage.clear()`,或直接跑 `main.py`。
- 阶段名用 `CS{n}_{动作}`;运营阶段时长 0。

## 引用核对(写 `_10` 前必做)

打开实际文件逐项核对,全部命中才写:

| `define_*` 参数 | 必须逐字等于 |
|---|---|
| `define_element` 的组名 | `_6` 中 `element.group.create(...)` 的组名 |
| `define_boundary` 的组名 | `_7` 中边界组名 |
| `define_loadcase` 的 `lc_name` | `_8` 中 `engine.load.create(<名>, ...)` 的工况名 |
| `define_analysis` 的工况名 | `_9` 中分析工况名 |

**工况名 ≠ 钢束名**:`define_loadcase` 只引用工况名(如 `预应力腹板束`),不引用钢束 shape 名(如 `N1-1`)。

## 体系转换

- 体系转换的激活和钝化放在**同一个阶段**里完成,拆到多个阶段会不收敛或成机构。
- 每个阶段激活的构件都要有落在已激活单元上的支承。
- 钢束张拉阶段不早于它所在单元的激活阶段。

## 失败模式

- **`阶段不存在`** —— 阶段编号不连续
- **`组不存在`** —— 组名不在 `_6`/`_7` 中,或差字符
- **`该工况中不存在名为 xxx 的预应力板束/荷载`(命令流 `StgLC,...`)** —— 引用了 `_8` 没创建或拼写不一致的工况名,或把钢束 shape 名当成了工况名。对照 `_8` 的 `load.create` 改一侧到逐字一致
- **`预应力工况需张拉/钝化的预应力所在的单元尚未激活`** —— 钢束跨进了本阶段还没激活的单元;调张拉阶段或缩钢束端点
- **`同一阶段内不允许重复激活单元组[xxx]`** —— 同阶段重复 `define_element`,或单跑 `_10` 前没清阶段
