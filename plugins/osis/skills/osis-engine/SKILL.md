---
name: osis-engine
description: OSIS 桥梁建模的总控入口。判断任务类型、按受力体系路由桥型、模板优先、写回 OSIS、失败修复、参数不足时用提问工具反问用户。当用户要从零建模、修改已有模型、在已有模型上加功能、求解、或建模报错需要定位时,先用本 SKILL。它只管流程,具体建模 API 在模块层,桥型方案在桥型层。
---

# osis-engine

## 三层

| 层 | 写什么 | SKILL |
|---|---|---|
| 总控 | 流程:任务分类、桥型路由、模板、写回、失败修复 | `osis-engine`(本文件) |
| 桥型 | 一种桥的方案:选模板和改模板的规程、方案默认值、钢束分类、契约名 | `osis-bridge-*` |
| 模块 | 一个 `_N` 文件的 API 写法和坑,不带桥型假设 | `osis-module-*` |

| 需求 | Skill |
|---|---|
| pyosis 通用用法与坑、查 API、控制画面 | `osis-python-helper` |
| 改跨中梁高 | `osis-edit-hmid` |
| 建模完成后自动评测:构造评分 + 受力评分 | `osis-auto-testconformance` |
| 荷载组合与规范验算、钢束优化 | `osis-check` |
| 生成计算书 | `osis-calcbook` |
| 自定义插件、用户/官方 skill、模型入库 | `osis-customize-osisai` |

## 会话硬约束

- **改了必须写回**:OSIS 的模型在 OSIS 进程里,不在 `py/` 文件里。改完 `.py` 要在同一轮执行写回(§写回),没执行不能说"已完成";用户明确说只改代码不执行时,报告里写明"按用户要求未执行"。同一份代码不要重复执行。
- **API 不确定先查**:用 OSIS MCP 的 `api_glob` / `api_grep` / `api_read`,其次看模块 SKILL 和模板代码。不去 WeKnora 查 API。
- **当前工程目录**:上下文给了就用;否则 `python -c "from pyosis import OSISEngine; print(OSISEngine().project.get_directory())"`。下文 `<project_dir>` 指它。
- **默认求快**:能复制模板就不构思,能最小改动就不重排;用户没给的参数用模板和桥型默认值,在完工报告里列出假设让用户纠正,不逐项反问。求快不省四样:算术自检、建模评测、桥型有歧义时的澄清、对不上支持桥型时的提示。
- **只动 `py/`**:不创建、修改、删除 `image/` `Check/` `Result/` `secmesh/` 等 OSIS 自动目录。
- **改模型必改画像**:见 §项目画像。
- **名字逐字一致**:`_6` 的单元组名、`_7` 的边界组名、`_8` 的工况名、`_9` 的分析工况名被下游按名引用,差一个字符就报"不存在"。
- **建模评测**:完整建模(含直接复制、小修)写回后自动调 `osis-auto-testconformance`,先出构造评分,再出受力评分(快速档)。两套分各自的总分、评级、偏差项写进完工报告,是否按偏差调整由用户定。局部修改不跑,除非用户要求。

## 任务分类

四类只选其一:

| 类型 | 判断 | 做法 |
|---|---|---|
| 完整建模 | 从零建一座桥,或按全新参数重建 | §路由桥型 → §模板优先策略 → 写回 → 评测 |
| 局部修改 | 在已有模型上改参数或加功能(荷载、阶段、边界、钢束…) | 改跨中梁高只加载 `osis-edit-hmid`;其余找到对应模块 SKILL,改 `.py`,写回,更新画像受影响的字段 |
| 求解/查询 | 模型已在 OSIS 里 | 直接 `OSISEngine().solve()` / 查询。**不要跑 `prep/main.py`**,它会清空模型重建 |
| 失败修复 | 建模或求解报错 | §失败修复流程 |

## 路由桥型

按**受力体系 + 施工方法**识别,加载唯一对应的桥型 SKILL。支持六种:

- 悬臂浇筑连续梁(节段悬浇、合龙、墩顶有支座) → `osis-bridge-cantilever-box`
- 变截面连续刚构(墩梁固结) → `osis-bridge-rigid-frame-box`。名称里有「刚构」就走这项,即使用户同时说了悬浇、变截面
- 预制小箱梁(简支 / 先简支后连续) → `osis-bridge-precast-small-box`
- 预制 T 梁(简支 / 先简支后连续) → `osis-bridge-precast-t-girder`
- 预制空心板 → `osis-bridge-hollow-slab`
- 常规现浇箱梁(整跨支架现浇,含匝道) → `osis-bridge-conventional-box`

完整建模时:

- 对得上其中一种:直接加载。
- 在几种之间有歧义:用提问工具让用户选。
- 一种都对不上:先用提问工具提示"套现有骨架可能建不对",选项为六种各一项 +「仍按最接近的类型试(不保证正确)」+「先不建」。用户选仍要试,就按最接近的一种做,完工报告写明"非支持桥型、按××试建、不保证正确"。

局部修改、求解、失败修复不走这道闸。

## 参数澄清

只在用户的话不足以无歧义推进时问。有提问工具(如 `question`)就用它,不要用普通文本提问;缺的参数打包成一次问完。

- 桥型清楚但缺参数:按桥型 SKILL 的 §必问参数 问。
- **选项第一项放"能直接命中模板的最接近参数"**,标注"有现成模板可直接复制,最快";用户自己报的值放第二项(复制后小修)。
- 走复制模板的路径时不逐项问 §必问参数:模板里的值就是默认值,完工报告列出假设。

## 模板优先策略

完整建模先用 SKILL 自带的模板,本地没有合适的再查 WeKnora,都没有才从零写。模板落到当前工程的 `<project_dir>/py/`(`prep/` + `项目画像.md`)。

`py/prep` 里已有模型时:先读画像告诉用户现有的是什么桥,问是否覆盖;没确认前不要 `seedtpl --force`,不要下载。

### 1. seedtpl

`<skill_dir>` = 本 SKILL.md 所在目录。有 OSIS MCP 的 `execute_python` 就用它跑(它不收命令行参数,用 `sys.argv` + `runpy` 传):

```python
import runpy, sys
script = r"<skill_dir>/scripts/seedtpl.py"
sys.argv = [script, "--spec", "<用户原话>"]
runpy.run_path(script, run_name="__main__")
```

没有 MCP 时在终端跑 `python "<skill_dir>/scripts/seedtpl.py" --spec "<用户原话>"`。

脚本按用户原话选桥型和最接近的模板,整目录复制过去,并在 stdout 打印 `共 N 个模板: [...]`。**看到这份全量名单之后才能说"命中"或"最接近的是哪份"**;名单像被截断就再跑一次。选哪份、算不算命中,按桥型 SKILL 的 §模板 判断。

### 2. WeKnora(本地没有合适模板时)

工具名可能带宿主前缀(如 `weknora_`、`mcp__weknora__`),按后缀认。

1. `list_knowledge_bases`,选桥梁模板/案例库(条目路径含 `02-案例库`),记下 `kb_id`。SKILL 列表、pyosis 库不是模板库。
2. `bridge_search_templates`(kb_id, query=用户原话或「桥型 + 跨径」)。
3. `download_bridge_template`(kb_id, case_query=案例目录名, dest_dir=`<project_dir>/py/`),文件直接写到当前工程 `py/` 下。
4. 读 `py/项目画像.md` 核对跨径、材料。

MCP 不可用或超时、没有模板库、搜索无命中、下载报错、`written_files` 为空:不要空等,按"未命中"处理。

用户问"有哪些知识库"时必须调 WeKnora 查,不要拿 SKILL 列表回答。

### 3. 按匹配度处理

| 匹配度 | 做法 |
|---|---|
| 精确命中 | 不改代码,跑 `main.py` |
| 近似命中 | 复制后只改差异,改法按桥型 SKILL 的 §模板;不要因为一项不同就换另一个跨径的模板 |
| 未命中 | 按 §从零建模 写 |

完工报告:以哪份模板为底、改了哪几处、假设清单(桥宽、材料、节段、钢束)、模型统计、评测结果。

## 从零建模

代码写在 `<project_dir>/py/prep/`,目录和各文件的函数名见 `references/template_layout.md`。按依赖顺序写,每个文件加载对应的模块 SKILL:

| 文件 | 内容 | 模块 SKILL |
|---|---|---|
| `_1_control.py` | 控制参数 | `osis-module-control` |
| `_2_property.py` | **只放钢束线型曲线**(`geometry.create_arc*`) | `osis-module-tendon` |
| `_3_material.py` | 材料、收缩徐变 | `osis-module-material` |
| `_4_section.py` | 截面(普通钢筋也写在这里) | `osis-module-section`、`osis-module-rebar` |
| `_5_node.py` | 节点 | `osis-module-node` |
| `_6_element.py` | 单元、单元组、构件理论厚度 | `osis-module-element` |
| `_7_boundary.py` | 边界、边界组 | `osis-module-boundary` |
| `_8_loadcase.py` | 工况、荷载、钢束规格与形状、预应力 | `osis-module-loadcase`、`osis-module-tendon` |
| `_9_analysis.py` | 沉降、车道、活载 | `osis-module-analysis` |
| `_10_stage.py` | 施工阶段 | `osis-module-stage` |

- 下游只引用上游已经创建的对象。
- 生成 `_6`/`_7`/`_8` 时,组和钢束形状的创建写成"存在就先删再建",这样单跑模块不会因同名失败。删除方式见 `references/incremental_rerun.md`。
- `main.py` 保持模板的结构:`with pyosis.batch():` 里先 `clear()`,再按 `_1`~`_10` 依次调用。`main.py` 不接受命令行参数。

## 项目画像

`<project_dir>/py/项目画像.md`,创建或修改模型后同步更新。

- 只记项目特定的事实(跨径、桥宽、材料、节段方案等),不写 API 和桥型通用内容。
- 拿不准的字段留空并标 `<!-- TODO -->`,不要凭推测填。
- 局部修改只改受影响的字段。
- 骨架和各节必含字段见 `references/profile_template.md`。

## 写回

改完 `.py` 后二选一:

| 方式 | 命令 | 什么时候用 |
|---|---|---|
| 单跑模块 | `python <project_dir>/py/prep/_N_xxx.py` | 改动只在这一个模块,且没改对象编号/名称、没删对象。同号同名重跑即覆盖,不清模型 |
| 全量重建 | `python <project_dir>/py/prep/main.py` | 其余情况:跨多个模块、改了编号或名称、删了对象、失败修复、`osis-edit-hmid`,以及拿不准时。先 `clear()` 再整桥重建 |

- **有 `execute_python` 就用它跑**:脚本路径传 `file=`,一两行的代码传 `code=`。它用 OSIS 环境的 Python(自带 pyosis)并连到当前实例;终端的 `python` 可能没装 pyosis,开了多个 OSIS 时还可能连错实例。全量重建耗时长,`timeout` 给足(如 600)。
- 脚本自带 `sys.path` 引导,不需要 `cd`。
- 单跑模块不清模型:删掉的对象不会消失,改了编号或名称会留下旧对象。单跑的其他注意事项(前置模块、组的重建、`_7` 重复分配)见 `references/incremental_rerun.md` §4。
- 不要用 `python -c` 写几句局部命令来代替写回,那样模型和 `py/` 会不一致。
- 后处理(验算、计算书)交给 `osis-check` / `osis-calcbook`。

## 失败修复流程

唯一的链路:**读报错原文 → 定位到模块 → 改对应的 `.py` → `prep/main.py` 全量重建**。

1. **读报错原文**:看命令流最后一段,报错在哪个 `_N`、哪个 API、哪个对象名。`BatchError` 不指明是哪条命令时,调试期在 `with` 块末尾加 `pyosis.flush(isolate=True)` 定位,定位后删掉。
2. **改 `.py` 到根因消除**。引用类报错同时打开引用方和被引用方两个文件,把名字改到逐字一致:只改一侧,不要两侧各造一个新名字。
3. **跑 `prep/main.py`**。

禁止:

- **没改代码就重跑**。每次重跑前要说得出"改了哪一行、为什么能消除上次的报错"。
- **同一个报错出现第 2 次还继续试**。停下来,把报错原文、已试过的修改、下一步假设列给用户,等确认。
- 把单独调用 `clear()` 当作修复。

报错 → 模块(完整对照表见 `references/error_diagnosis.md`):

| 报错涉及 | 看 |
|---|---|
| 位移异常、机构、未定义边界条件 | `osis-module-boundary` |
| 钢束(`LayoutTS`、夹角、控制点超范围、出梁) | `osis-module-tendon` |
| 组不存在 | `osis-module-element` + 引用方 |
| 工况不存在、阶段激活失败(`StgLC`) | `osis-module-loadcase` + `osis-module-stage`,两边对照名字 |
| 几何检查不通过、截面参数 | `osis-module-section` |
