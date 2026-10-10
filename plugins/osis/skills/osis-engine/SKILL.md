---
name: osis-engine
description: OSIS 桥梁建模的总控入口。判断任务类型、按受力体系路由桥型、编排模块加载顺序、维护建模状态、规范与 OSIS 软件的交互(状态化原则、清屏、求解、replot)、参数不足时用提问工具反问用户。当用户要从零建模、修改已有模型、在已有模型上加功能、求解、或建模报错需要定位时,先用本 SKILL。它只做编排与调度,不含具体建模 API、桥型特征、模块层规则。
---

# osis-engine

> 总控。决定"做什么、谁来做、什么顺序、怎么交接"。具体建模规则在桥型层和模块层。

## 三层与工具索引

| 层 | 职责 | SKILL |
|---|---|---|
| 总控 | 任务分类、桥型路由、模块编排、状态维护、与 OSIS 交互 | `osis-engine`(本文件) |
| 桥型 | 桥型方案(节点序列、组名清单、阶段序列、桥型特有失败模式) | `osis-bridge-{bridge_type}` |
| 模块 | API 用法、约束、错误归因。**不带桥型假设,跨桥型通用** | `osis-module-{module_type}` |

| 需求 | 调用的 Skill |
|---|---|
| 任何任务的总入口(必先加载) | `osis-engine` |
| 桥型方案(由本文件路由) | `osis-bridge-{bridge_type}` |
| 写 `_1`..`_10` 任意模块 | 对应 `osis-module-{module_type}` |
| 模板匹配 | 本文件 §模板优先策略(WeKnora 优先,失效再 `seedtpl`),各 bridge `references/templates/` |
| 荷载组合与规范验算 | `osis-check` |
| 生成计算书 | `osis-calcbook` |
| pyosis 用法要点与坑(签名用 MCP `api_glob`/`api_grep`/`api_read` 查) | `osis-python-helper` |
| 改跨中梁高 / h_mid | `osis-edit-hmid` |
| 建模完成后构造正确性自动评测 | `osis-auto-testconformance` |
| 自定义插件、用户/官方 skill、模型入库 | `osis-customize-osisai` |

## 会话硬约束

- **先总控再下游**:未加载本 SKILL 不得直接开写模块或猜桥型
- **改了必须执行**:改 `.py` ≠ 模型已变,创建或修改的代码必须直接执行写回(用户明确要求 dry-run 除外);OSIS 在代码调用时已保存结果,同一份代码不要重复执行
- **API 不确定先查**:禁止凭印象猜,查法见 §与 OSIS 软件交互
- **当前工程目录**:上下文已给出就用;否则执行 `python -c "from pyosis import OSISEngine; print(OSISEngine().project.get_directory())"` 读取。下文 `<project_dir>` / `get_directory()` 均指它
- **默认求快**:用户没另说时走最快路径——能复制模板不构思、能最小 diff 不重排;未指定参数用模板/桥型默认,完工报告列假设请用户纠正,不逐项反问。改了 `py/` 的写回按 §写回 选单模块或 `main.py`,不用 `python -c` 局部命令代替。求快不裁四样:**算术闭合自检**、**构造评测**(本条末)、**桥型歧义时的澄清**、**对不上六种支持桥型时的提示**
- **只动 `py/`**:不创建/修改/删除 `image/` `Check/` `Result/` `secmesh/` 等 OSIS 自动目录
- **改模型必改画像**:同步更新 `项目画像.md`,字段缺失留 `<!-- TODO -->`
- **组名逐字一致**:`_6` 组名被 `_8`/`_9`/`_10` 引用,差字符报"组不存在"
- **构造评测**:完整建模(含直接复制/小修)完成后自动调 `osis-auto-testconformance`,总分/评级/偏差项写入完工报告,是否按偏差调整由用户定。"越快越好"不压缩评测

## 接到任务后,先做这些

1. **判断任务类型**。4 类只选其一。
2. **若是完整建模或局部修改,先路由桥型**。完整建模接着做 §模板优先策略。其余类型跳到第 4 步。
3. **按模块依赖顺序加载对应 SKILL**。
4. **若是求解/查询,直接走 OSIS 交互规范**。
5. **若建模失败,按报错对象类型定位到模块 SKILL**。

## 任务分类

- 完整建模 —— 用户从零建一座桥,或按全新参数重建。链:路由桥型 → §模板优先策略 → 近似则小修、未命中才按序生成全部模块 → 生成模型。
- 局部修改 —— 在已有模型上改参数或加功能(新增荷载/阶段/边界/钢束等,**不是**完整建模)。链:**改跨中梁高 / h_mid → 只加载 `osis-edit-hmid`** → 其余定位模块 SKILL 改对应 `.py` → **同一轮写回**(单模块或 `prep/main.py`,见 §写回)。写回后只更新画像受影响字段;加功能默认不因此做构造评测。
- 求解/查询 —— 模型已存在,只求解或读状态。直接 `engine.solve()` / `engine.model_summary()`。不要 `main.py`。
- 失败修复 —— 建模或求解报错。链:读报错原文 → 定位报错模块 → **修改对应 `.py`** → **同一轮 `prep/main.py` 写回**(详见 §失败修复流程)。

> **不要把"求解已有模型"误判为"完整建模"**。`prep/main.py` 会清空模型,求解已有模型只调 `engine.solve()`。

## 路由桥型

按**受力体系 + 施工方法**识别,加载唯一对应的桥型 SKILL。当前能正确落地的只有这六种:

- 悬臂浇筑连续梁(节段、合龙) → `osis-bridge-cantilever-box`
- 先简支后连续 / 预制小箱梁 → `osis-bridge-precast-small-box`
- 预制 T 梁 / 先简支后连续 T 梁 → `osis-bridge-precast-t-girder`
- 变截面连续刚构(墩梁固结、无永久支座) → `osis-bridge-rigid-frame-box`。**名称里有「刚构」即走本项**,即使用户同时写了悬浇/变截面/大箱梁
- 常规现浇箱梁(整跨支架现浇、无体系转换,含匝道) → `osis-bridge-conventional-box`
- 预制简支空心板(闭口空心截面,中小跨) → `osis-bridge-hollow-slab`

**完整建模**时:对得上六种之一 → 直接加载。六种之间歧义(如箱梁 vs 刚构) → 澄清,不要臆测。对不上任何一种 → **先**用提问工具提示:套现有骨架可能建不对。options 为六种各一项 +「仍按最接近的类型试(不保证正确)」+「先不建」。选六种之一则按该项路由;选仍要试则路由最接近的一种,完工报告写明「非支持桥型、按××试建、不保证正确」;选先不建则停止。不要普通文本提问,不要不提示就硬套。

局部修改 / 求解 / 失败修复不走这道闸。

## 模块协作 DAG(完整建模)

完整建模按以下顺序生成,不可跳步、不可重排。**这是模块层之间的依赖关系**,本 SKILL 只搬运这个图,具体约束在对应模块 SKILL。

```
_1 控制 → _2 几何属性 → _3 材料 → _4 截面 → _5 节点
                                    ↓
                              _6 单元(依赖 材料+截面+节点)
                                    ↓
                              _7 边界(依赖 节点)
                                    ↓
                              _8 荷载(依赖 单元+材料+几何, 含钢束)
                                    ↓
                              _9 分析(依赖 节点+单元组, 含车道/沉降)
                                    ↓
                              _10 阶段(依赖 全部组)
```

模块对应的 SKILL:`_1`→`osis-module-control`,`_4`→`osis-module-section`,`_8`→`osis-module-loadcase`+`osis-module-tendon`,`_9`→`osis-module-analysis`,`_10`→`osis-module-stage`。其余类推。

**`_2` 几何属性的处理**:`_2_property.py` 是**钢束线型曲线**文件,内容全部是 `engine.geometry.create(...)` 调用(为每条钢束建 ARC2D/ARC3D 锚固曲线,在 `_8` 钢束 shape 创建时引用)。API 详见 `osis-module-tendon` 的"线型曲线"小节。

> 收缩徐变在 `osis-module-material` 创建材料时绑定,坐标系通常不需要(沿用 OSIS 全局坐标系)。这 2 类**不**出现在 `_2_property.py`。

按桥型额外引入:`osis-module-tendon`(任何含预应力)、`osis-module-rebar`(任何需要精细配筋)。**其他模块层引入条件、模块顺序在对应桥型 SKILL 决定**。

代码写入位置:应严格写入到当前打开项目的 `py/prep/` 文件夹中(_N 模块文件)+ 同级 `项目画像.md`。目录树与 builder 名见 `references/template_layout.md`。

- 每个 `_N_xxx.py` 的内容是 `def build_*(engine):` 函数,函数体里就是对应 `osis-module-xxx` 展示的示例代码(`_1` 是 `setup_control`,其余是 `build_*`)
- 模板命中/未命中见 §模板优先策略
- 入口:`python <project_dir>/py/prep/main.py`(`main.py` 和 `_N_xxx.py` 都自带幂等的 `sys.path` 引导,任何目录都能跑)

## 模板优先策略(完整建模)

路由桥型后**先 WeKnora 下载,失败再自己跑 `seedtpl.py`**。落盘目标一律当前工程 `get_directory()/py/`(`prep/` + 同级 `项目画像.md`)。`py/prep` 已有模型时先读画像说明现有桥型,问是否覆盖;未确认不要下、不要 `seedtpl --force`。

### 1. WeKnora(优先)

工具名可能带宿主前缀(如 `weknora_`、`mcp__weknora__`),按后缀认。

1. `list_knowledge_bases` → 选桥梁模板/案例库(条目路径含 `02-案例库`),记下 `kb_id`。不要把 SKILL 列表或 pyosis 库当成模板库。
2. `bridge_search_templates`(kb_id, query=用户原话或「桥型 + 跨径」)
3. 命中案例后 `download_bridge_template`(kb_id, case_query=案例目录名, dest_dir=`get_directory()/py/`)。该工具把 `prep-md/*.py.md` 拆成真正的 `.py`,文件直接写在当前工程 `py/` 下。
4. 读 `py/项目画像.md` 核对跨径/材料,再按下表匹配度动作。

下列任一情况视为 WeKnora 失效,立刻改走 §2,不要空等、不要手搓:`MCP 不可用或超时` / `list_knowledge_bases` 没有模板库 / 搜索无命中 / 下载报错 / `written_files` 空。

### 2. seedtpl(降级)

只在 WeKnora 失效时,由主会话直接在终端跑本 SKILL 的脚本(`<skill_dir>` = 本 SKILL.md 所在目录):

```bash
python "<skill_dir>/scripts/seedtpl.py" --spec "<用户原话>"
```

有 OSIS MCP 的 `execute_python` 就用它跑(原因见 §执行方式;默认目标 `get_directory()` 也取自该实例)。它不收命令行参数,用 `sys.argv` + `runpy` 传:

```python
import runpy, sys
script = r"<skill_dir>/scripts/seedtpl.py"
sys.argv = [script, "--spec", "<用户原话>"]
runpy.run_path(script, run_name="__main__")
```

stdout 的 `共 N 个模板: [...]` 即全量名单;**未报全量不得宣布命中/近邻**。N 对不上或名单像截断 → 再跑,或 `ls` 当前桥型 `references/templates/`。只查本桥型平铺目录(没有 `<桥型>/<跨径>` 两级)。

悬浇三跨只改跨径(近似命中、节段对数相同):不要手改 `_5`/`_2`,按 `osis-bridge-cantilever-box` 跑它的 `spanremap`,看 stdout 校核。失败则换同构近邻。

| 匹配度 | 动作 |
|---|---|
| 精确命中(跨径 + 桥宽 + 截面一致) | 信任模板,跑 `main.py` |
| 近似命中(跨径差一档 / 桥宽 / 材料不同,或 n / 节段与用户指定冲突) | 复制后只改差异,不要换另一跨径。悬浇三跨跨径 → `spanremap`;刚构/其余钢束按桥型最小 diff。预制梁:冻结端密簇,`Δ` 只进标准段 |
| 未命中 | 按 §模块协作 DAG 从零写 |

复制路径跳过桥型 §必问参数逐项反问。完工报告列出假设(桥宽/材料/节段/钢束)+ 模型统计 + 构造评测(见 §会话硬约束)。近似命中还要写清以哪份为底、改了哪几处。幂等见 `references/incremental_rerun.md`。

## 维护建模状态

每生成一个模块,把对象写入建模状态。下游模块只能引用状态里已有的对象,引用未创建的对象是错误。

| 字段 | 记录 |
|---|---|
| `profile` | 桥型、跨径、桥宽、截面、施工方法、规范 |
| `sections` | 截面编号、名称、类型、变截面控制点 |
| `nodes` | 支点、锚固点、变截面点、合龙点、横隔板点 |
| `elements` | 单元编号范围、材料、截面、分组名 |
| `boundaries` | 支座节点、约束类型、激活阶段 |
| `loads` | 工况、车道、引用单元组 |
| `tendons` | 钢束名、锚固点、投影组、张拉阶段 |
| `stages` | 阶段名、激活的构件/边界/荷载/钢束 |

## 维护项目画像

**创建或修改任何模型后,同步更新项目画像**(与 `prep/` 同级的 `项目画像.md`,即位于 `py/项目画像.md`)。

- 字段只记项目特定事实(跨径、桥宽、材料、节段方案等)。共性参数、API 细节、桥型特征不写,那些在 SKILL 里。
- 字段缺失时留空并标 `<!-- TODO -->`,不要凭推测填。
- 局部修改后,只更新受影响的字段,不要重写整个文件。

项目画像的 9 节骨架、每节必含字段、占位规则详见 `references/profile_template.md`(母模板,各 `templates/<bridge>/项目画像.md` 复制此骨架后填项目特定字段)。

## 参数澄清(提问工具)

当且仅当用户的提示不足以无歧义推进时,用宿主自带的提问工具(如 `question`)反问。**有提问工具时不要用普通文本提问**。

- 信息够且对得上六种之一 → 直接路由桥型,推进
- 桥型清楚但缺几何/材料参数 → 路由到对应桥型 SKILL,按其 §"必问参数"清单打包反问
- 桥型/任务描述不明确(六种之间歧义) → 反问让用户选
- 完整建模但对不上六种 → 按 §路由桥型提示后再继续或停止
- **options 推荐项锚定模板库**:反问时把「能精确命中模板的最近参数」放第一项,标注"有现成模板可直接复制,最快";用户自报的参数保留为次选(走复制+小修)。让用户顺手选模板参数 = 后续零构思,求快闭环(见 §会话硬约束 · 默认求快)

(具体必问参数表、推荐 option、参数取值范围都在各桥型 SKILL §"必问参数"一节,本 SKILL 不重复)

## 与 OSIS 软件交互(状态化原则)

OSIS 是状态化软件:模型数据驻留在 OSIS 进程内,不在 `py/` 文件里。所有操作围绕这一点展开。

### 写回:单模块或全量重建

**改代码 ≠ 写回 OSIS**。`.py` 只是磁盘脚本。改完 `.py` 后、向用户报完工前,**同一轮执行写回**,二选一:

- **单跑模块** `python <project_dir>/py/prep/_N_xxx.py`:每个模块的 `__main__` 只在 `batch()` 里执行本模块,不清模型。仅当**改动只在这一个模块、且没改对象编号/名称、没删对象**时用(同号/同名重跑即覆盖)。前置模块、组的 delete-if-exists、`_7` 的 `assign` 重复分配等注意见 `references/incremental_rerun.md §5`。
- **全量重建** `python <project_dir>/py/prep/main.py`:先 `clear()` 再按 `_1`..`_10` 整桥重建。改动跨多个模块、改了编号/名称、删了对象、失败修复、`osis-edit-hmid`,以及拿不准时,一律用它。

禁止未执行时说「已完成 / 已改好 / 功能已加上」;未跑完最多说「代码已改,正在执行写回」。例外仅当用户明确说「先别跑 / 只改代码不要执行 / dry-run」,报告写明「按用户要求未执行」。

只求解、不改模型: `OSISEngine().solve()`,不要 `main.py`。

`add_rebar_s("ShearStirrup", ...)` 在截面上已有同类型箍筋时,OSIS 可能仍返回成功、模型却不更新。生成 `_4` 时对已有箍筋先 `delete_rebar_s("ShearStirrup")` 再 add。不要给模板 `_4` 首次建模嵌一套 [VERIFY] 打印块。

**查 API 优先顺序**(写新代码时):① OSIS MCP 的 `api_glob` / `api_grep` / `api_read`(用法要点与坑见 `osis-python-helper`)→ ② `osis-module-*` SKILL / 模板 `prep/_N` → ③ pyosis 源码。不去 WeKnora 查 API。Stage 工期属性是 `.duration`(无 `get_duration()`)。用户问「有哪些知识库」必须调 Weknora,不得用 SKILL 列表代替。

### 改跨中梁高 → `osis-edit-hmid`

用户要改跨中梁高 / h_mid / 跨中截面高度:**只加载 `osis-edit-hmid`**,按其步骤改 `_4`(必要时 `_5`)。改完跑 `main.py` 写回。**禁止**改钢束、禁止构造评测。

### 执行方式

| 场景 | 命令 | 说明 |
|---|---|---|
| 写回(全量) | `python <project_dir>/py/prep/main.py` | 先 `clear()` 再整桥重建 |
| 写回(单模块) | `python <project_dir>/py/prep/_N_xxx.py` | 只执行本模块,条件见 §写回 |
| 求解已有模型 | `python -c "from pyosis import OSISEngine; OSISEngine().solve()"` | 模型已在 OSIS 中,只求解,不改 `py/` |

**有 OSIS MCP 的 `execute_python` 就优先用它**:脚本路径传 `file=`,求解这类一两行的传 `code=`。它用 OSIS 环境的 Python(自带 pyosis)并连到当前实例;终端 `python` 可能没装 pyosis,开了多个 OSIS 时还可能连错。全量重建耗时长,`timeout` 给足(如 600)。没有 MCP 时才用上表的终端命令。

> `clear()` 只在 `main.py` 入口处。单跑 `_N_xxx.py` 不清空全桥:删掉的对象不会消失,改了编号/名称会留下旧对象,这些情况必须全量重建。

**批量执行 `with pyosis.batch():`(默认用)**:块内命令只进本地缓冲,退出时拼成一条命令流一次发给 OSIS,比逐条发送快得多。模板 `main.py` 已用 `with batch():` 包住 `clear()` 到 `_10`;新写或改 `main.py` 保持这个结构,其他一次性下大量命令的脚本也包一层。

- 块内的查询(`get`/`all`/`count`/`solve` 等)会先自动冲刷缓冲再执行,结果是实时的,但会打断批量。建模段里不要穿插查询
- 块内 Python 抛异常 → 尚未发送的缓冲命令全部丢弃(块内若有查询,查询前的命令已执行)
- OSIS 执行失败抛 `BatchError`(带 OSIS 原文,不指明是哪条)。要定位坏命令:调试时在 `with` 块末尾加一行 `pyosis.flush(isolate=True)`,失败时二分列出出错命令。二分会重复发送已成功的命令,非幂等的 create 可能误报,只用于调试,定位后删掉这行

`main.py` 与 `_N_xxx.py` 入口都有幂等的 `sys.path.insert`,从任何目录跑都能 import 同目录的 `_0_engine.py`。`OSISEngine()` 实例化时自动连接当前打开的 OSIS 项目,**不需要 `cd`**。

`main.py` 不接受命令行参数,不要写 `python prep/main.py --solve`。只改代码不执行、未改代码就重跑 `main.py` 的禁令见 §写回 与 §失败修复流程。

### Engine 便捷操作

```python
from pyosis import OSISEngine
e = OSISEngine()

e.clear()                # 清空模型(慎用,需用户确认;只允许出现在 main.py 全量入口,见 §幂等)
e.clc()                  # 清屏
e.solve()                # 求解
e.replot()               # 重绘
e.save_project()         # 保存项目
e.model_summary()        # 模型汇总(⚠️ 部分 OSIS 版本缺 GetAllRespSpecInfo 接口会在 dynamic.count() 抛"接口不通";此时改用分项 count:e.node.count()/e.element.count()/e.material.count()/e.section.count()/e.load.count()/e.stage.count())
e.export_apdl(path)      # 导出前处理状态为 .out
e.import_apdl(path)      # 读 .out / .sml
```

后处理(验算、计算书)交给 `osis-check` / `osis-calcbook`,**不在本流程内**读结果。

## 幂等(生成代码时)

全量重建靠 `main.py` 里的 `clear()`;单跑模块靠同号/同名覆盖(适用条件见 §写回)。生成 `_6`/`_7`/`_8` 时,组/形状创建写成 delete-if-exists,单跑模块或同一次重建里同名创建都不会失败。可用的删除方式见 `references/incremental_rerun.md`。

## 失败修复流程(铁律)

报错后的**唯一**合法链路:

```
读报错原文 → 定位报错模块 → 修改对应 .py → prep/main.py 全量重建
```

1. **读报错原文**。看命令流最后一段:报错发生在哪个 `_N` 阶段、哪个 API、涉及哪个对象名。
2. **对照修改 `.py`**。打开相关 `_N_xxx.py` 修改到根因消除。**引用类报错要同时打开引用方与被引用方两个文件**(如 `_10` 引用 `_8` 的工况名、"组不存在"涉及 `_6` 与 `_8`/`_9`/`_10`),把名字改到逐字一致——只改一侧,不要两侧各改出一个新名字。
3. **跑 `prep/main.py`**(同一轮必须已跑)。未执行写回不得报完工。

**绝对禁止**:

- **未修改任何 `.py` 就重跑 `main.py`**。不改代码重跑必然在同一处再次报错。
- **连续两次全量重建之间没有代码 diff**。每次跑 `main.py` 前,必须能明确说出"这次改了哪一行、为什么能消除上次的报错";说不出来,就先回去改代码。
- **同一个报错出现第 2 次**。说明上次改动没打中根因——停止重跑,把报错原文、已试过的修改、下一步假设列给用户,等用户确认后再动。
- 把单独调用 `e.clear()` 当作修复。`clear()` 只出现在 `main.py` 里;错的是 `py/` 里的代码。

报错涉及的**对象类型** → 模块 SKILL 定位表(详细错误信号见 `references/error_diagnosis.md`):

- 位移异常、机构失稳 → `osis-module-boundary`
- 钢束报错(夹角、范围、layout) → `osis-module-tendon`(命令流 `LayoutTS,<名>` → 改 `_2` 里同名曲线的控制点 x;见该 SKILL §改跨径时怎么改钢束)
- 组找不到、节点不存在 → `osis-module-element` + 引用方
- **工况中不存在、阶段激活失败(含 `StgLC` 报错)** → `osis-module-loadcase` + `osis-module-stage`(两边对照工况名)
- 几何检查不通过、截面参数错 → `osis-module-section`
- 其他 → 逐模块 SKILL 排查
