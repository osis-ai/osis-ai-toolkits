---
name: osis-check
description: 荷载组合与规范验算(JTG),以及验算结果检查分析。当用户需要(1)做组合与验算、(2)查看验算结果、(3)分析NG项原因、(4)生成验算报告 时使用。
---

# osis-check

## 工作流

```
用户请求
    │
    ▼
求解（模型改过就重新求解）
    │
    ▼
组合与验算：跑 py/post/main.py（没有就先用 scripts/gen_post.py 生成）
    │
    ▼
导出验算结果
    │
    ▼
加载项目画像，分析报告
    │
    ▼
用户是否要求修改？
    ├── 否 → 结束
    └── 是 → 进入修改流程
```

> **定位项目目录**：`python -c "from pyosis import OSISEngine; print(OSISEngine().project.get_directory())"`，所有文件操作基于此路径。建模代码在 `<项目目录>/py/prep/`，后处理代码在 `<项目目录>/py/post/`。

用户说明**已在 OSIS 里验算过**、之后没再改模型，跳过步骤 1、2，直接从步骤 3 导出结果。

## 步骤1：求解

组合与验算用的是已经算好的工况结果和活载包络，自己不求解。`prep/main.py` 只重建，不产生结果；模型在求解后又改过（含重建），必须重新 `solve()`。没求解就组合，OSIS 报「未定义包络/工况类型」，这不是工况类型没写。

```bash
python -c "from pyosis import OSISEngine; OSISEngine().solve()"
```

## 步骤2：组合与验算（py/post/main.py）

组合与验算写成工程里的 pyosis 代码 `py/post/main.py`，和 `py/prep/` 一样可读、可改、可重跑：每次运行先删掉全部组合与验算再重建，结果只跟文件内容有关。

**没有 `py/post/main.py` 时先用本 skill 的脚本生成**（模型须已重建，不必先求解；写到 `<项目目录>/py/post/main.py`，已有的会覆盖）：

```bash
python scripts/gen_post.py --construct Pre     # 预制梁：空心板、T 梁、小箱梁
python scripts/gen_post.py --construct Cast    # 现浇：现浇箱梁、悬浇连续梁、连续刚构
```

- 按模型里的工况生成，规则同 OSIS 5.1「自动组合与验算」：基本 / 标准 / 频遇 / 准永久组合及包络；温度按工况类型 `T`（整体升降温）、`TG`（梯度）识别；沉降组进组合；活载频遇、准永久系数 = ψ/(1+μ)（μ 按活载工况里的基频，JTG D60-2015 4.3.2，取三位小数）。
- 构件类型默认 `APC`（A 类部分预应力，一般梁桥），后张。用户或画像写明全预应力 / B 类 / 先张时加 `--member EPC|BPC`、`--tension Pre`。
- **工况、活载工况、沉降组改了要重新生成**；只改材料、截面、钢束等不用。

**运行**（求解之后）：

```bash
python py/post/main.py
```

大模型（悬浇、刚构）组合 + 验算可能超过 1 小时，文件里已 `set_timeout(10800)`；经 MCP `execute_python` 跑时 `timeout` 也要给够。

**按需求改 `py/post/main.py`**，这是用代码验算比 GUI「自动组合与验算」（只在 GUI 里有、固定全部单元全部验算项）好的地方：

| 需求 | 改法 |
|------|------|
| 只验算部分单元（如主梁、某一跨） | `post.select_elements("S", "1to20")`，`A` 添加、`U` 去掉 |
| 只开部分验算项 | `post.set_check_items('[{"UltM":1,"Shear":1}]')` |
| 改构件类型 / 施工方式 | `post.set_member_type("EPC", "Cast", "Post")` |
| 增删组合、改系数 | 改对应的 `create_combine` / `add_to_combine`，包络（`OR`）里同步增删成员 |
| 某验算项换用的组合 | 改 `add_check(验算项, 组合或包络名)` |

验算项代号、包络与结果表的对应。结果表是 `<项目目录>/Check/<材料或荷载组>_<验算项>_<组合>.lcc`，如 `混凝土_正截面抗弯验算_基本组合包络.lcc`、`施工阶段荷载包络_PC施工阶段正截面压应力验算_MinMax.lcc`：

| 代号 | 验算项 | 默认用的包络 |
|------|--------|------------|
| `UltM` | 正截面抗弯验算 | 基本组合包络 |
| `UltN` | 正截面抗拉压验算 | 基本组合包络 |
| `Shear` | 斜截面抗剪验算 | 基本组合包络 |
| `SSNC` | PC使用阶段正截面压应力验算 | 标准组合包络 |
| `SSPC` | PC使用阶段斜截面主压应力验算 | 标准组合包络 |
| `CrackS` | PC正截面短期抗裂验算 | 频遇组合包络 |
| `CrackWeb` | PC腹板斜截面抗裂验算 | 频遇组合包络 |
| `CrackWidth` | 裂缝宽度验算（RC / B 类） | 频遇组合包络 |
| `CrackL` | PC正截面长期抗裂验算 | 准永久组合包络_直接作用、准永久组合包络 |
| `CSNC` | PC施工阶段正截面压应力验算 | MinMax（施工阶段荷载包络） |
| `CSNT` | PC施工阶段正截面拉应力验算 | MinMax |

**坑**：
- 求解器里默认没有选中单元，不调 `select_elements` 就报「目前无选中单元」；`set_member_type`、`set_check_items` 也要在选中单元之后。
- `check_all()` 读的是 `<项目目录>/Check/*.lcc`，之前跑过、这次已删掉的验算项的旧表还在。减少验算项或改组合名之后，先删掉 `Check/` 下的旧文件再跑，或只看本次 `add_check` 对应的表。

## 步骤3：导出验算结果

```python
from pyosis import OSISEngine

engine = OSISEngine()
results = engine.result.check_all()
for name, df in results.items():
    result_col = next((c for c in df.columns if str(c).strip() == '结果'), None)
    if result_col is None:
        print(f'{name}: EMPTY')
        continue
    values = df[result_col].astype(str).str.strip()
    ng = int(values.str.contains('NG', na=False).sum())
    status = 'EMPTY' if len(df) == 0 else ('NG' if ng else 'OK')
    print(f'{name}: {status}  ({len(df)} 项, NG={ng})')
```

`EMPTY` 表示导出 0 行，不能视为通过（裂缝宽度验算对 PC 构件通常就是 0 行）；若是用户点名的目标验算项，先确认已在当前模型上求解并跑过步骤 2。

用户只要报告、没有具体要求时，全导出大致过一遍就出报告。有具体需求再用：

- `scripts/export_all_checks.py`：导出所有验算结果并统计 OK/NG
- `scripts/load_lcc.py`：按单个或模式加载 `.lcc` 文件
- `scripts/analyze_item.py`：分析指定 `.lcc` 验算项并输出 NG 详情
- `scripts/extreme_values.py`：生成极值汇总和单元级最不利安全系数报告

## 步骤4：加载项目画像

检查 `py/项目画像.md` 是否存在。如存在，读取桥梁体系、截面类型、跨径、施工方法、预应力体系等，用于桥型判定和构件类型（预制/现浇、A 类/全预应力）。如不存在，标注"未找到项目画像，按通用桥型分析"。

## 步骤5：分析并生成报告

### 用户只要报告（未提及"修改"）

1. 总结验算结果
2. 根据桥型，结合桥梁工程专业知识确定验算侧重点和控制指标
3. 报告包括：桥型判定；针对性验算重点；各验算项通过/不通过；NG 项数量和位置；不通过原因分析；修改建议方向（仅参考，不执行）
4. 停止，不进入修改流程

> 默认直接输出，不用写文件。

### 用户要求修改/优化/调整

1. 确认项目画像存在（不存在建议先创建）
2. 用任务列表工具规划任务
3. 导出验算结果，分析 NG 项原因
4. 查看 `py/prep/` 模块文件获取模型信息
5. 定位原因时 **reason_code 用 `py/reason_codes.yaml` 里的短码**（项目里没有就用本 skill 的 `references/reason_codes.yaml`），不要自造
6. 先分清是模型问题还是验算设置问题（构件类型、施工方式、组合、选中单元）：后者改 `py/post/main.py`，前者按桥型制定修改策略：

   | 桥型 | 关注重点 |
   |------|---------|
   | 箱梁 | 截面应力、扭转、剪力 |
   | 预制梁 | 横向分布、接缝、单片稳定 |
   | 大跨桥 | 施工阶段、徐变、预拱度 |

7. 将方案作为选项返回给用户选择，按选中的方案修改（模型改动见下方「与其他 skill 协作」）
8. **修改后重验**：重新求解（步骤 1），再跑 `py/post/main.py`（步骤 2），再导出（步骤 3）

**核心原则**：先识别桥型 → 先整体后局部 → 先承载力后正常使用。

## 行为约束

| 场景 | 行为 |
|------|------|
| 用户仅要报告 | 不要列 todolist、不要查模型文件、不要查修改函数 |
| 未明确要求 | 不要假设用户需要修改、不要主动提供修改代码 |
| 修改模型时 | 必须结合画像中的桥型、截面、施工方法等信息制定策略 |
| 为让某项通过而改验算设置时 | 构件类型、施工方式要与桥的实际设计一致，不能为了过验算降标准；改了要在回复里说明 |

## 与其他 skill 协作

| 场景 | Skill |
|------|-------|
| 截面承载力不足，需增大截面 | `osis-module-section` |
| 预应力不满足，需调整钢束 | `osis-module-tendon` |
| 配筋不足或过大 | `osis-module-rebar` |
| 活载工况设置不合理（含冲击系数基频） | `osis-module-analysis` |
| 施工阶段相关 NG | `osis-module-stage` |
| 材料/边界/荷载/分析等参数调整 | `osis-engine` |
