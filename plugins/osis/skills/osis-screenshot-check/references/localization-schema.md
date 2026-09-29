# 视觉问题定位

## 按顺序定位

1. 将问题的 `region` 和可选粗略框映射到模型纵向范围。
2. 读取该范围内的节点、相邻单元、截面指派和偏移。
3. 读取生成这些对象的当前项目源文件。
4. 将视觉现象映射到一个候选对象和一个候选字段。
5. 从当前项目画像、项目设计事实和相邻对象确定目标值。
6. 记录 `source_state_consistency`、`localization_status` 和缺失事实。

## 保持来源分离

- 将截图问题记录为 `visual_observation`。
- 将当前项目代码记录为 `project_source_state`。
- 将当前 OSIS 只读摘要记录为 `live_model_state`。
- 不得把视觉现象直接解释成某个字段错误。
- 不得因截图判错而跳过当前代码和实时状态核对。
- 项目源正确而实时模型或视觉观察冲突时设置 `repair_status = unsafe_to_apply`；不得修改项目源或重建实时模型。

## 要求唯一性

- 仅在一个源文件、一个对象、一个字段和一个目标值同时唯一时设置 `localization_status = exact`。
- 多个问题、多个字段都能解释现象或目标值不唯一时设置 `localization_status = ambiguous`。
- 只能定位到视觉区域时设置 `localization_status = visual_only`。
- 让 `ambiguous` 和 `visual_only` 进入 `repair_status = unsafe_to_apply`。

## 按需读取标准案例

- 不得把桥型路由或标准案例设为 `incorrect` 的成立条件。
- 仅在当前项目画像和项目设计事实不足以确定语义、对象映射或目标值时读取一个最相关案例。
- 只用标准案例确认结构不变量或字段语义。
- 不得从近似案例复制尺寸、编号、节点位置或修改值。
- 无可用案例时保留 `visual_verdict = incorrect`；仅把自动修复降为 `unsafe_to_apply`。
