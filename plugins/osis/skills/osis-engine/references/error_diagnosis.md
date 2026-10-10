# 错误诊断参考表

> OSIS 报错的总索引;每个错误的具体修复方法由对应模块 SKILL 提供。

## 报错 → 根因 → 解决

| 报错特征 | 根因 | 解决方向 |
|---|---|---|
| `Uz >> 1e5` / 某方向位移超大 | 边界 0/1 写反,某自由度本应约束却释放 | 检查所有 `create_general` 参数 —— **不写 = 约束(1),写 0 = 释放**。重点查单梁 Ry/Rw |
| `Uz >> 1e5` / Stage 1 简支梁节点位移异常 | 临时支座设置在当前阶段尚未激活的节点或单元范围外,导致阶段结构端点变成悬臂 | 临时支座应放在该阶段实际活动构件的端点节点上,例如"预制梁端节点"而非"现浇段节点",并与阶段激活的单元组一致 |
| `Ry自由度位移=1e10` | 单梁模型未约束绕 Y 轴转动 | 至少一个支座 `ry=1`(`create_general` 默认即 1) |
| `BatchError: 批量冲刷失败（共 N 条命令）` | `with batch()` 里某条命令被 OSIS 拒绝,原文在冒号后 | 按原文定位模块;原文看不出是哪条时,在 `with` 块末尾临时加 `pyosis.flush(isolate=True)` 重跑,会列出失败命令 |
| `组不存在` / `load group not found` | `_6` 的组名与 `_8`/`_9`/`_10` 引用的名字不一致 | 对比三处引用,改到逐字一致(含中文/下划线/数字) |
| `夹角大于90度` | 钢束相邻控制点连线折返(点太密或半径太大) | 回到原曲线的点数和半径,只按区移 x;见 `osis-module-tendon` §改跨径时怎么改钢束 |
| `形状控制点坐标超出参照单元组的坐标范围` | 钢束曲线的 x 范围超出了 `element_group` 覆盖的节点 x 范围 | 检查 `create_arc3d` 的 x 坐标是否在单元组首尾节点 x 之间 |
| `shape.layout('GLOBAL')` 报错 / 预应力工况需张拉/钝化的预应力所在的单元尚未激活 | 钢束曲线终点或投影组跨越了当前阶段尚未激活的单元 | 确保钢束线型端点和投影单元组都限制在当前阶段已激活的单元范围内,必要时同步缩回到当前阶段的活动单元组 |
| `工况结果不存在,请先求解` | 施工阶段分析的结果不能按单独工况名导出 | 调 `osis-check` 做组合验算,不要直接 `result.loadcase()` |
| `StgLC,...` / `该工况中不存在名为 xxx 的预应力板束(或荷载)` | `_10` 的 `define_loadcase` 引用了 `_8` 未创建或拼写不一致的工况名;或误把钢束 shape 名(如 `N1-1`)当工况名引用 | 打开 `_8_loadcase.py` 逐条 `load.create` 对照,把 `_10` 的引用名改到逐字一致(只改一侧);改后跑 `main.py`,禁止不改代码重跑 |
| `Section,1,xxx...` 参数错误 | 截面 API 参数数量/顺序不匹配 | 用 `api_read` 核对截面 API 参数(`osis-module-section`) |
| `该参数组合几何检查不通过` | 用默认尺寸但桥型缩小,参数不自洽 | 从目标 h/bt/bb 反推全部几何参数,不可只改一处 |
| `弹性连接报错` | 弹簧单元组激活时 `define_element` 的 `birth` 不是 0 | 弹簧单元组 `birth=0.0`;混凝土单元组用激活龄期 |
| `非法输入：{64}` / 命令流 `AsgnBd,n,a,{64}` | `boundary.assign("a", {64})` 把 Python set 写进命令 | 改成 `assign("a", 64)` 或 `"2to4"` / list;禁止 set |
| `Solve` / `CSn：未定义边界条件,或者边界条件未定义在已激活单元上` | 本阶段激活的构件没有可用支承(assign 用了 set 没写进去,或支座/临时支架节点不在本阶段已激活的单元上) | 先修 `_7` 的 assign;确认该阶段激活了对应边界组,且边界节点在已激活单元上 |
| `同一阶段内不允许重复激活单元组` | 单跑 `_10` 前没清阶段,或同阶段重复 `define_element` | 删重复行;单跑 `_10` 前先 `engine.stage.clear()`,或跑 `main.py` |
| `add_rebar_s` / `RebarS` 无报错但箍筋没变 | 截面上已有同类型 ShearStirrup,二次 add HTTP 成功但模型不更新 | 先 `delete_rebar_s("ShearStirrup")` 再 add;用 `section.get(no).rebar.has_shear_stirrup` 读回 |
| `ImportError: cannot import name 'text_encoding' from 'io'` | 没用会话里的 `python`(PATH 上已配好) | 用 `python`,不要用系统旧解释器 |
| `ModuleNotFoundError: No module named 'pyosis'` | 没用会话里的 `python` | 用 `python`(已装 pyosis);装库 `python -m pip` |
| `AssertionError: SRE module mismatch` | Python 多版本冲突 | 用 `python`,不要另开系统解释器 |

## 施工阶段问题排查三步

1. 这个阶段激活了哪些单元组?
2. 支座/临时支座在哪个节点?这个节点是否在当前阶段激活的单元上?
3. 钢束曲线 x 范围和投影组是否都落在已激活单元范围内?
