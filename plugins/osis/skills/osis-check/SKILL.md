---
name: osis-check
description: 验算结果检查分析工具。当用户需要(1)查看验算结果、(2)分析NG项原因、(3)生成验算报告 时使用。
---

# osis-check

## 工作流

```
用户请求
    │
    ▼
生成组合并验算（如未验算过）
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

在调用此 SKILL 之前，**项目必须已构建并求解完成**。如尚未验算，先执行步骤1；如已验算过，跳过步骤1直接从步骤2导出结果。

> **定位项目目录**：执行 `python -c "from pyosis.core.engine import OSISEngine; print(OSISEngine().project.get_directory())"` 获取 OSIS 打开的项目目录，所有文件操作基于此路径。

## 步骤1：生成组合并验算

用户**未说明如何验算**时：

```bash
python -c "from pyosis import OSISEngine; OSISEngine().post.combination_and_check()"
```

（`combination_and_check` 由 `PostManager` 提供,无参数）

用户如果说明他**已在 OSIS 中进行了验算**，跳过此步。

## 步骤2：导出验算结果

```python
from pyosis import OSISEngine

engine = OSISEngine()
results = engine.result.check_all()
for name, df in results.items():
    ok = len(df)
    ng = sum(1 for row in df.itertuples(index=False) for v in row if 'NG' in str(v))
    print('{name}: {status}  ({ok} 项, NG={ng})'.format(name=name, status='NG' if ng else 'OK', ok=ok, ng=ng))
```

如果用户没有太具体要求，只让生成报告，直接参考示例把所有验算结果全导出并大致过一遍即可，尽快将报告生成出来。如果有具体需求，再参考其他脚本进行细致的分析：

- `scripts/export_all_checks.py`：导出所有验算结果并统计 OK/NG
- `scripts/load_lcc.py`：按单个或模式加载 `.lcc` 文件
- `scripts/analyze_item.py`：分析指定 `.lcc` 验算项并输出 NG 详情
- `scripts/extreme_values.py`：生成极值汇总和单元级最不利安全系数报告

## 步骤3：加载项目画像

检查 `py/项目画像.md` 是否存在。如存在，读取并提取桥梁体系、截面类型、跨径、施工方法、预应力体系等关键信息，用于桥型判定。如不存在，标注"未找到项目画像，按通用桥型分析"。

## 步骤4：分析并生成报告

### 用户只要报告（未提及"修改"）

1. 总结验算结果导出输出
2. 根据项目画像中的桥型信息，结合桥梁工程专业知识，自主确定验算侧重点和控制指标
3. 生成报告，包括：
   - 桥型判定（基于画像或模型特征）
   - 针对性验算重点（根据桥型确定）
   - 各验算项目通过/不通过状态
   - NG 项数量和位置
   - 不通过原因分析
   - 修改建议方向（仅参考，不执行）
4. 停止，不进入修改流程

> 默认直接输出，不用写文件。

### 用户要求修改/优化/调整

1. 确认项目画像存在（不存在建议先创建）
2. 规划任务列表（todowrite）
3. 导出验算结果，分析 NG 项原因
4. 查看 py/ 模块文件获取模型信息
5. 若存在 `py/reason_codes.yaml`（或本 skill `references/reason_codes.yaml`），定位原因时 **reason_code 必须用其中的短码**，不要自造
6. 根据桥型特征制定修改策略：

   | 桥型 | 关注重点 |
   |------|---------|
   | 箱梁 | 截面应力、扭转、剪力 |
   | 预制梁 | 横向分布、接缝、单片稳定 |
   | 大跨桥 | 施工阶段、徐变、预拱度 |

7. 调 `osis-engine` 执行修改
8. 将方案作为选项返回给用户选择
9. **修改后重验**:执行步骤1（已有设置自动复用）+ 步骤2

**核心原则**:先识别桥型 → 先整体后局部 → 先承载力后正常使用。

---

## .lcc 文件命名约定

`<sheetType>_<checkItem>_<checkName>.lcc`,示例:

- `混凝土_正截面抗弯验算_基本组合.lcc`
- `一般_裂缝宽度验算_频遇组合.lcc`
- `施工阶段荷载包络_PC施工阶段正截面压应力验算_CS1.lcc`

格式不符自动跳过。

## 行为约束

| 场景 | 行为 |
|------|------|
| 用户仅要报告 | 不要列 todolist、不要查模型文件、不要查修改函数 |
| 未明确要求 | 不要假设用户需要修改、不要主动提供修改代码 |
| 生成报告时 | 必须先加载项目画像，按桥型给出针对性分析 |
| 修改模型时 | 必须结合画像中的桥型、截面、施工方法等信息制定策略 |
| 输出定位 JSON 时 | `reason_code` 必须来自 `py/reason_codes.yaml` 或本 skill `references/reason_codes.yaml` |

## 与其他 skill 协作

| 场景 | Skill |
|------|-------|
| 验算前必须先完成组合 | 本 skill |
| 截面承载力不足，需增大截面 | `osis-module-section` |
| 预应力不满足，需调整钢束 | `osis-module-tendon` |
| 配筋不足或过大 | `osis-module-rebar` |
| 活载工况设置不合理 | `osis-module-analysis` |
| 施工阶段相关 NG | `osis-module-stage` |
| 材料/边界/荷载/分析等参数调整 | `osis-engine` |