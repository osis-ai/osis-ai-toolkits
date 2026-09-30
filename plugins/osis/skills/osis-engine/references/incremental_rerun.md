# 幂等与删除命令实测手册

> 写回 OSIS 一律 `execute_python(file=".../prep/main.py", cwd="<project_dir>")`
> (先 `clear()` 再整桥重建)。不要用单模块重跑或 `osis-l0-hot` 代替,
> 也不要用本地 shell 跑 `python`。
> 本文件只保留生成代码时用得上的 delete 命令和幂等事实(2026-07 实机)。下面旧的「禁止 main.py」表不再作为写回规则。

## 0. 写回

改了 `py/` 就用 `execute_python(file=".../prep/main.py", cwd="<project_dir>")` 写回。不要 `osis-l0-hot`,不要 `python -c` 局部写回,不要单跑 `_N_xxx.py`。只求解且不改 `py/` 时用 `OSISEngine().solve()`(经 `execute_python(code=...)` 执行)。

## 1. 三个根因:为什么以前"改一处就要全量重建"

| 根因 | 现象 | 解法 |
|---|---|---|
| `engine.clear()` 写在 `main.py` 入口 | 跑 `main.py` = 清空全桥重来 | 这就是现在的写回方式。生成代码时组/形状仍写 delete-if-exists(见 §3) |
| 单元组/边界组/钢束形状的 `create` 非幂等 | 重跑 `_6`/`_7`/`_8` 报"已经存在" | 生成代码时一律写 delete-if-exists(见 §3);整模块重跑也可 scoped clear(见 §7) |
| pyosis `delete()` 依赖 `GetReferences` 接口,部分 OSIS 版本不通 | 删对象抛"接口不通: GetReferences" | 用组删除或原始命令(见 §4) |

## 2. create 幂等性实测矩阵

**覆盖语义(同名/同号重跑 = 更新,不报错),可放心单模块重跑:**

| API | 实测依据 |
|---|---|
| `node.create(no, ...)` | 同 no 重跑覆盖 |
| `material.create_conc/create_steel/...` | 同 no 覆盖 |
| `section.create_*` | 同 no 覆盖 |
| `element.create_beam3d/create_spring/...` | 同 no 覆盖 |
| `boundary.create_general/...` | 同 no 覆盖 |
| `load.create(name, type, scalar)`(工况) | 同名覆盖 |
| `lc.create_gravity` / `lc.create_line_load` 等(工况上加载) | 同工况同实体**覆盖,不重复累加** |
| `settlement.group.create(name, val, *nodes)` | 同名覆盖 |
| `live.grade.create_highway` | 同名覆盖 |
| `stage.create(no, name, duration)` | 同 no 覆盖 |
| `geometry.create_arc2d/arc3d/spl3d`(样条) | 同名覆盖 |
| `tendon.prop.create*`(钢束特性) | 同名覆盖 |
| `element.taper_group.create`(变截面组) | 同名覆盖(生成或修改) |

**非幂等(同名报"已经存在"/"创建失败"),重跑前必须 delete-if-exists:**

| API | 报错原文(实测) |
|---|---|
| `element.group.create(name, "c")` | 单元组[name]已经存在 |
| `boundary.group.create(name, "c")` | 边界组已存在 |
| `tendon.shape.create_arc2d/arc3d/spl3d` | 创建钢束形状 [name] 失败 |

## 3. 生成代码时的幂等写法(强制)

`_6_element.py` / `_7_boundary.py` / `_8_loadcase.py` 中,组和钢束形状创建**一律**写成:

```python
# 单元组
if engine.element.group.get("主梁单元"):
    engine.element.group.delete("主梁单元")     # 组删除无依赖检查,可直接用
eg = engine.element.group.create("主梁单元", "c")
eg.add("1to88")

# 边界组
if engine.boundary.group.get("永久约束组"):
    engine.boundary.group.delete("永久约束组")
bg = engine.boundary.group.create("永久约束组", "c")
bg.add(1, 2)

# 钢束形状(tendon.shape.delete 在部分 OSIS 版本因 GetReferences 不通而不可用,用原始命令)
if engine.tendon.shape.get("BB2-z"):
    engine.run("TdShapeDel,BB2-z")
shape = engine.tendon.shape.create_arc2d("BB2-z", 2, "15-19", "BB2-zGp", 1, "BB2-z_VerCurve", "BB2-z_HorCurve")
shape.layout("ELEMENT", 1, 0, 0, 0.0, 0.0, 0.0)
```

`main.py` 的推荐结构(clear 只在此处):

```python
def main(engine=None) -> None:
    eng = default_engine if engine is None else engine
    eng.clear()          # ← 只允许出现在这里
    eng.clc()
    setup_control(eng)   # _1 只设参数,不含 clear
    build_property(eng)
    # ... 其余模块
```

## 4. 删除方式对照表(绕过 GetReferences 不通)

pyosis 的 `node/element/section/material/boundary/loadcase/tendon.prop/tendon.shape/live.grade` 的 `delete()` 内部先调 `get_dependencies()` → `GetReferences` HTTP 接口;该接口在部分 OSIS 版本不存在(报"接口不通: GetReferences"),导致这些 `delete()` **整体不可用**。实测可用的替代:

| 对象 | 推荐删除方式 |
|---|---|
| 单元组 / 边界组 / 沉降组 | `element.group.delete(name)` / `boundary.group.delete(name)` / `settlement.group.delete(name)`(无依赖检查,直接用) |
| 施工阶段 | `stage.delete(no)`(参数是**编号 int**,走 `StageDel,no`,不经 GetReferences) |
| 节点 | `engine.run("NodeDel,<no>")` |
| 单元 | `engine.run("ElementDel,<no>")` |
| 截面 | `engine.run("SectionDel,<no>")` |
| 材料 | `engine.run("MaterialDel,<no>")` |
| 边界 | `engine.run("BoundaryDel,<no>")` |
| 荷载工况 | `engine.run("LoadCaseDel,<name>")` |
| 钢束特性 | `engine.run("TdPropDel,<name>")` |
| 钢束形状 | `engine.run("TdShapeDel,<name>")` |
| 样条曲线 | `engine.run("Spline3DDel,<name>")` |
| 活载等级 | `engine.run("LiveGradeDel,<name>")` |

注意:绕过依赖检查的删除可能留下悬空引用(例如删了仍被单元引用的截面),只用于"准备立刻重建该对象"的场景——这正是 delete-if-exists 的用途。

## 5. 各模块单模块重跑速查

写回不要用这张表。改了 `py/` 跑 `main.py`。下表只说明各模块单独执行时的覆盖行为。

| 模块 | 能否单跑 | 前置条件 | 注意 |
|---|---|---|---|
| `_1_control` | 可以 | — | 只设参数,不含 clear |
| `_2_property`(样条) | 可以 | 无 | 样条同名覆盖 |
| `_3_material` | 可以 | 无 | 同 no 覆盖;改材料编号会影响下游引用 |
| `_4_section` | 可以 | `_3` 已建 | 同 no 覆盖;TaperEle 同名覆盖 |
| `_5_node` | 可以 | 无 | 同 no 覆盖;改坐标即更新 |
| `_6_element` | 可以 | `_3`/`_4`/`_5` 已建 | **组必须 delete-if-exists** |
| `_7_boundary` | 可以 | `_5` 已建 | **边界组必须 delete-if-exists**;`b.assign` 重复执行会重复分配,重跑前可用 `assign("r", ...)` 或 `"s"` 替换 |
| `_8_loadcase`(含钢束) | 可以 | `_3`/`_6` 已建 | **shape 必须 delete-if-exists**;工况/加载同名覆盖 |
| `_9_analysis` | 可以 | `_5`/`_6` 已建 | 沉降组/活载等级同名覆盖 |
| `_10_stage` | 可以 | `_6`/`_7`/`_8`/`_9` 的组名/工况名已在 | 同 no 覆盖;纯引用模块,最适合单跑 |

## 6. 其他实测坑

- `engine.model_summary()` 在缺 `GetAllRespSpecInfo` 接口的 OSIS 版本上抛"接口不通"(卡在 `dynamic.count()`)。改用分项:`e.node.count()` `e.element.count()` `e.material.count()` `e.section.count()` `e.load.count()` `e.stage.count()` `e.geometry.count()` `e.tendon.count()`(返回 `{"props": n, "shapes": n}`)。
- `StageManager` 无 `rename`;阶段改名用同 `no` 重新 `create(no, 新名, duration)`。
- 查询类方法(`get`/`all`/`count`)随时可用,不影响模型状态;重跑模块后先查 count 验证再进下一步。

## 7. scoped clear:按类清空,整模块重跑的另一条路(2026-07-30 立项)

重跑整个非幂等模块时,除了逐对象 delete-if-exists(§3),还有更省事的一条路:**每个管理器都有自己的 `clear()`,只清本类对象,不动其他,更不做 `engine.clear()` 全清**。pyosis 源码核实:

| 调用 | 清掉什么 |
|---|---|
| `engine.geometry.clear()` | 全部样条曲线 |
| `engine.material.clear()` / `engine.section.clear()` / `engine.node.clear()` / `engine.element.clear()` | 全部材料/截面/节点/单元 |
| `engine.element.group.clear()` / `engine.boundary.group.clear()` | 全部单元组/边界组 |
| `engine.boundary.clear()` | 全部边界 |
| `engine.load.clear()` | 全部荷载工况 |
| `engine.tendon.clear()` | 全部钢束形状+特性(= `shape.clear()` + `prop.clear()`) |
| `engine.stage.clear()` | 全部施工阶段 |
| `engine.live.clear()` / `engine.settlement.group.clear()` | 活载/沉降组 |

**铁律:clear 的实现是逐个 `delete`,任一对象被下游引用就抛 `清空所有XX失败: ...被占用,无法删除`(已删的不回滚)。必须按依赖逆序清——先清引用别人的,再清被引用的;`stage` 永远最先清、最后重跑:**

- 重跑 `_8_loadcase`:`stage.clear()` → `tendon.clear()` + `load.clear()`,然后重跑 `_8`;`_10_stage` 必须跟着重跑(阶段已被清掉)。
- 重跑 `_6_element`:`stage.clear()` → `tendon.clear()`(钢束形状引用单元组)→ `element.group.clear()`,然后重跑 `_6`;`_8`/`_10` 跟着重跑。
- 重跑 `_2_property`(改样条):`stage.clear()` → `tendon.clear()`(钢束形状按名引用曲线)→ `geometry.clear()`,然后重跑 `_2`;`_8`/`_10` 跟着重跑。
- 越上游级联越大。只想改一两根钢束/一两个组时别用 clear,退回 §3 的 delete-if-exists 粒度更细、无级联。

**版本警告**:clear 内部走各对象的 `delete()`,对象级 delete 依赖 `GetReferences` 接口(§4);在该接口不通的 OSIS 版本上,对象级 clear 同样失败(组级 clear 不受影响)。遇此情况退回 §4 的原始命令逐个删。

## 8. 验证

写回是否成功,看这次 `main.py` 有没有无 traceback 跑完。查询类方法(`get`/`all`/`count`)可以在重建之后用来核对,不能代替重建。

