# 直接视觉判断

## 校验输入

- 读取冻结的当前项目画像。
- 直接查看 `before-body.png`、`before-left.png`、`before-middle.png`、`before-right.png`。
- 使用全梁图检查整体连续性和对称关系。
- 使用左段、跨中段、右段检查局部轮廓、截面过渡和构件完整性。
- 让相邻分段的重叠区保持一致。
- 任一必要图像无法显示、主体不足、遮挡严重或视角不适合时返回 `screening_result = unjudgeable`。
- 项目画像只提供当前项目的设计先验，不能代替截图观察。
- 不得从像素统计、边缘检测或程序计算结果生成视觉结论；不得代替多模态视觉判断。

## 直接判断

- 发现明显几何异常时返回 `screening_result = incorrect`。
- 发现截图与当前项目画像明确不符时返回 `screening_result = incorrect`。
- 未发现明显视觉异常时返回 `screening_result = no_obvious_anomaly`。
- 无法可靠比较时返回 `screening_result = unjudgeable`。
- 仅在 `incorrect` 时写 `visual_verdict = incorrect`；其余写 `visual_verdict = null`。
- 不得输出 `correct`，不得把“未发现明显视觉异常”扩大为整个模型正确。

## 明显问题示例

- 相邻单元出现非设计台阶、折角或错位。
- 单个短单元的轮廓明显偏离左右相邻单元。
- 构件中断、缺失、整体偏移或镜像不一致。
- 截面内部轮廓出现明显畸变。
- 端部、过渡区、跨中区的可见变化方向与项目画像相反。

将这些项目作为非穷举示例；只要可见问题清楚或与画像明确冲突即可判错。

## 结果结构

写入：

```json
{
  "screening_result": "incorrect",
  "visual_verdict": "incorrect",
  "reviewed_views": ["full", "left", "middle", "right"],
  "issues": [
    {
      "issue_id": "issue-1",
      "issue_type": "profile_mismatch",
      "region": "right",
      "description": "右过渡区的可见变化方向与当前项目画像相反。",
      "bbox_normalized": [0.62, 0.2, 0.92, 0.88]
    }
  ],
  "summary": "发现一处明显视觉异常。"
}
```

- 让 `incorrect` 至少包含一个问题。
- 让 `no_obvious_anomaly` 和 `unjudgeable` 使用空问题列表。
- 让 `no_obvious_anomaly` 和 `unjudgeable` 使用 `visual_verdict = null`。
- 只校验粗略框位于 `[0, 1]`；不得要求逐点坐标、像素边缘锚定或前景包络命中。
- 让三段图只用于放大观察，不把每一段变成独立证据门。
